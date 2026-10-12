#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza visualizador_3d_sitio.html (e index.html) para exibir TODA a divisória do terreno usando o SIGSC:
1. Relevo ESTENDIDO cobrindo 100% da divisa do sítio (18,60 ha) com o MDT LiDAR 1,0 m SIGSC
2. Textura Oficial SIGSC 0,39 m cobrindo toda a área (1250 m x 1350 m = 168 ha)
3. Tubo 3D perimetral da divisa completo (1635 vértices contínuos sobre o relevo, sem cortes)
4. Preserva 100% do Simulador Solar Astronômico (estações do ano, hora solar, telemetria, zênite, azimute)
5. Reflete com fidelidade matemática todas as construções de visualizador_casa_arredores.html:
   - Casa do Sítio (200 m², alinhada aos KMZs telhado1 e telhado2, cota natural 540,95m sem montículo)
   - Salão de Festas (12×8m = 96 m², 100% aberto, sem estacas, usina 36 módulos em ambos os lados, 3 opções)
   - Quadra de Areia (22×12m, 10 postes H=6m, telas Sul, Leste e Norte H=6m, lado Oeste aberto, rede oficial)
   - Chalés 1 a 5 (22 m² cada, sobre pilotis no relevo, e Chalés 4 e 5 girados na direção da Casa do Sítio)
6. visualizador_casa_arredores.html permanece 100% intocado.
"""

import os
import io
import json
import base64
import shutil
import rasterio
from rasterio.enums import Resampling
import numpy as np
from PIL import Image
import geopandas as gpd

SOLAR_DIR = r"C:\Users\haas\github\solar"
MDT_TIF = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Estendida.tif")
ORTO_TIF = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Area_Estendida.tif")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")

HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")
INDEX_OUT = os.path.join(SOLAR_DIR, "index.html")

def main():
    print("================================================================================")
    print("GERANDO VISUALIZADOR 3D COM TODA A DIVISÓRIA USANDO SIGSC OFICIAL")
    print("================================================================================")

    # 1. Leitura do MDT LiDAR SIGSC Estendido
    print("1. Lendo MDT LiDAR 1,0 m SIGSC da área estendida...")
    with rasterio.open(MDT_TIF) as src_m:
        elev = src_m.read(1)
        b = src_m.bounds
        left, bottom, right, top = float(b.left), float(b.bottom), float(b.right), float(b.top)
        rows, cols = elev.shape

    width_m = right - left
    depth_m = top - bottom
    cx = (left + right) / 2.0
    cy = (bottom + top) / 2.0

    z_min = float(np.nanmin(elev))
    z_max = float(np.nanmax(elev))
    z_range = z_max - z_min
    print(f"   Dimensões do Terreno: {width_m:.1f} m x {depth_m:.1f} m (Grade nativa: {cols} x {rows})")
    print(f"   Centro do Modelo 3D: E {cx:.2f}, N {cy:.2f}")
    print(f"   Cotas SIGSC: Mínima = {z_min:.2f} m | Máxima = {z_max:.2f} m | Desnível = {z_range:.2f} m")

    elev_clean = np.where(np.isnan(elev), z_min, elev)

    # Grade WebGL otimizada a 625 x 675 vértices (passo de 2,0m) para renderização ultra-fluida
    step_grid = 2
    elev_sub = elev_clean[::step_grid, ::step_grid]
    sub_rows, sub_cols = elev_sub.shape
    print(f"   Malha WebGL: {sub_cols} x {sub_rows} = {sub_cols*sub_rows:,} vértices")

    uint16_arr = np.round(((elev_sub - z_min) / z_range) * 65535).astype(np.uint16)
    b64_heights = base64.b64encode(uint16_arr.tobytes()).decode('ascii')

    # 2. Leitura da Ortofoto Oficial SIGSC 0,39 m
    print("2. Codificando textura Ortofoto SIGSC 0,39 m em alta definição...")
    tex_w = 2500
    tex_h = int(round(tex_w * depth_m / width_m))
    with rasterio.open(ORTO_TIF) as src_o:
        rgb = src_o.read([1, 2, 3], out_shape=(3, tex_h, tex_w), resampling=Resampling.bilinear)

    img = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    b64_tex = base64.b64encode(buf.getvalue()).decode('ascii')
    print(f"   Textura SIGSC: {tex_w}x{tex_h} px ({len(b64_tex)/1024/1024:.2f} MB em Base64)")

    # 3. Amostragem da Divisa Completa do Sítio (18,60 ha) sobre o MDT SIGSC
    print("3. Amostrando divisa completa do sítio (18,60 ha) sobre o relevo...")
    res_x = width_m / cols
    res_y = depth_m / rows

    def sample_poly_3d(poly, step=1.5, dz=0.75):
        ext = poly.exterior
        total_len = ext.length
        num_pts = max(int(total_len / step), len(ext.coords))
        pts = []
        for d in np.linspace(0, total_len, num_pts):
            pt = ext.interpolate(d)
            col = int((pt.x - left) / res_x)
            row = int((top - pt.y) / res_y)
            col = max(0, min(cols - 1, col))
            row = max(0, min(rows - 1, row))
            h = float(elev_clean[row, col]) - z_min + dz
            pts.append([round(pt.x - cx, 2), round(h, 2), round(-(pt.y - cy), 2)])
        return pts

    gdf_sitio = gpd.read_file(GPKG_PATH, layer='limite_sitio')
    sitio_coords_3d = sample_poly_3d(gdf_sitio.geometry.iloc[0], step=1.5, dz=0.85)
    print(f"   Divisa do Sítio 100% Contínua: {len(sitio_coords_3d)} vértices em torno de toda a propriedade!")

    setores_coords = {}
    for s in ['p1', 'p2', 'p3']:
        gdf_s = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{s}')
        poly_s = gdf_s.union_all().convex_hull.buffer(3.5)
        setores_coords[s] = sample_poly_3d(poly_s, step=2.0, dz=0.60)

    # 4. Mesas Fotovoltaicas de Solo (233 mesas)
    print("4. Carregando mesas fotovoltaicas de solo...")
    tables_data = []
    for setor in ['p1', 'p2', 'p3']:
        gdf = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor}')
        for _, r in gdf.iterrows():
            c = r.geometry.centroid
            tables_data.append({
                'setor': setor.upper(),
                'id': str(r['mesa_id']),
                'x': round(c.x - cx, 2),
                'y': round(r['cota_painel_inferior_m'] - z_min, 2),
                'z': round(-(c.y - cy), 2),
                'cota': float(r['cota_terreno_m'])
            })

    # 5. Coordenadas Locais das Edificações no Relevo SIGSC Estendido
    rot_rad = -0.489038 # -28.02°

    casa_utm = (663415.50, 6968636.50)
    cota_casa = 540.95
    casa_data = {
        'utm': casa_utm,
        'cota': cota_casa,
        'x': round(casa_utm[0] - cx, 2),
        'z': round(-(casa_utm[1] - cy), 2),
        'y': round(cota_casa - z_min, 2),
        'cx_utm': casa_utm[0],
        'cy_utm': casa_utm[1]
    }

    salao_utm = (663445.60, 6968642.80)
    cota_salao = 547.10
    salao_data = {
        'utm': salao_utm,
        'cota': cota_salao,
        'x': round(salao_utm[0] - cx, 2),
        'z': round(-(salao_utm[1] - cy), 2),
        'y': round(cota_salao - z_min, 2),
        'rot_rad': rot_rad
    }

    quadra_utm = (663456.88, 6968636.85)
    cota_quadra = 547.25
    quadra_data = {
        'utm': quadra_utm,
        'cota': cota_quadra,
        'x': round(quadra_utm[0] - cx, 2),
        'z': round(-(quadra_utm[1] - cy), 2),
        'y': round(cota_quadra - z_min, 2),
        'rot_rad': rot_rad
    }

    chales_raw = [
        {"id": 1, "utm": [663457.29, 6968674.96], "cota": 551.91},
        {"id": 2, "utm": [663448.54, 6968667.08], "cota": 549.73},
        {"id": 3, "utm": [663438.93, 6968659.26], "cota": 547.07},
        {"id": 4, "utm": [663466.65, 6968618.00], "cota": 549.02},
        {"id": 5, "utm": [663469.69, 6968600.54], "cota": 549.40}
    ]
    chales_data = []
    for c in chales_raw:
        e, n = c["utm"]
        chales_data.append({
            'id': c['id'],
            'utm': c['utm'],
            'cota': c['cota'],
            'x': round(e - cx, 2),
            'z': round(-(n - cy), 2),
            'y': round(c['cota'] - z_min, 2)
        })

    # 6. Montagem do HTML completo com Three.js e Simulador Solar Astronômico
    print("5. Gerando HTML unificado com toda a divisória SIGSC e simulador solar...")
    html_code = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D — Sítio das Andorinhas (Divisa Completa 18,60 ha & 100% SIGSC)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      overflow: hidden;
      background: #0f172a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #f8fafc;
    }}
    #canvas-container {{ width: 100vw; height: 100vh; }}
    
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 385px;
      background: rgba(15, 23, 42, 0.94); color: #f8fafc; padding: 18px;
      border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.6);
      border: 1px solid rgba(255,255,255,0.14); backdrop-filter: blur(14px);
      z-index: 10; max-height: calc(100vh - 32px); overflow-y: auto;
    }}
    h1 {{ font-size: 16px; font-weight: 700; margin-bottom: 3px; color: #38bdf8; }}
    .badge {{ display: inline-block; font-size: 10.5px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background: #0369a1; color: #fff; margin-bottom: 8px; }}
    .badge-sigsc {{ background: #059669; }}
    
    .stat-row {{ display: flex; justify-content: space-between; font-size: 11.5px; padding: 3.5px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    .stat-lbl {{ color: #94a3b8; }}
    .stat-val {{ font-weight: 600; color: #4ade80; }}
    .stat-highlight {{ color: #fbbf24; font-weight: 700; }}
    
    .slider-box {{ margin-top: 10px; background: rgba(30, 41, 59, 0.7); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }}
    .slider-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; font-size: 11px; color: #cbd5e1; }}
    .slider-val {{ font-weight: 700; color: #38bdf8; }}
    input[type=range] {{ width: 100%; accent-color: #38bdf8; cursor: pointer; }}
    
    .btn-group {{ margin-top: 10px; display: flex; flex-direction: column; gap: 5px; }}
    .btn {{
      background: #0284c7; border: none; color: white; padding: 7px 10px;
      border-radius: 6px; cursor: pointer; font-size: 11.5px; font-weight: 600;
      transition: all 0.2s; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px;
    }}
    .btn:hover {{ background: #0369a1; transform: translateY(-1px); }}
    .btn-secondary {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; }}
    .btn-secondary:hover {{ background: #334155; }}
    .btn-accent {{ background: #059669; }}
    .btn-toggle-active {{ border-left: 4px solid #fbbf24; }}
    .btn-opt {{ font-size: 11px; padding: 6px 5px; text-align: center; border-radius: 6px; cursor: pointer; transition: all 0.2s; }}
    .btn-opt-active {{ background: #0284c7 !important; color: #ffffff !important; font-weight: 700 !important; border: 1px solid #38bdf8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }}

    #loading {{
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(15, 23, 42, 0.96); color: #38bdf8; padding: 24px 36px;
      border-radius: 12px; font-size: 15px; font-weight: 600; border: 1px solid rgba(255,255,255,0.15);
      box-shadow: 0 10px 40px rgba(0,0,0,0.7); text-align: center; z-index: 100;
    }}
    .spinner {{
      margin: 0 auto 12px auto; width: 32px; height: 32px;
      border: 3px solid rgba(56, 189, 248, 0.2); border-top-color: #38bdf8;
      border-radius: 50%; animation: spin 0.8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="loading">
    <div class="spinner"></div>
    Carregando Terreno Completo SIGSC & Divisória 18,60 ha...<br>
    <span style="font-size: 11px; color: #94a3b8;">MDT LiDAR 1,0 m e Ortofoto SIGSC 0,39 m</span>
  </div>

  <div id="canvas-container"></div>

  <div id="panel">
    <h1>🌐 SÍTIO DAS ANDORINHAS 3D</h1>
    <div class="badge badge-sigsc">100% SIGSC Oficial (Divisória 18,60 ha Completa)</div>
    
    <div class="stat-row"><span class="stat-lbl">Área da Propriedade:</span><span class="stat-val">18,60 ha (186.016 m²)</span></div>
    <div class="stat-row"><span class="stat-lbl">Área Renderizada 3D:</span><span class="stat-val">{width_m:.0f} × {depth_m:.0f} m (168,7 ha)</span></div>
    <div class="stat-row"><span class="stat-lbl">Cotas SIGSC:</span><span class="stat-val">{z_min:.1f} m a {z_max:.1f} m</span></div>
    <div class="stat-row"><span class="stat-lbl">Casa do Sítio:</span><span class="stat-val">200 m² (Cota 540,95 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">Salão 12x8m:</span><span class="stat-val">36 módulos solares TOPCon</span></div>
    <div class="stat-row"><span class="stat-lbl">Quadra de Areia:</span><span class="stat-val">22 × 12 m (Telas H=6 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">Chalés 1 a 5:</span><span class="stat-val">22 m² cada (Pilotis no relevo)</span></div>
    <div class="stat-row"><span class="stat-lbl">POTÊNCIA TOTAL USINA:</span><span class="stat-val stat-highlight">2.460 kWp (2,46 MWp)</span></div>

    <!-- Link para Visualizador Detalhado -->
    <a href="visualizador_casa_arredores.html" target="_blank" class="btn" style="width: 100%; margin-top: 8px; font-size: 11px; text-decoration: none; background: #0284c7; border: 1px solid #38bdf8;">
      🏡 Abrir Visualizador Detalhado (Casa do Sítio & Arredores)
    </a>

    <!-- SIMULADOR SOLAR ASTRONÔMICO -->
    <div class="slider-box" style="border: 1px solid rgba(251, 191, 36, 0.4); background: rgba(30, 41, 59, 0.85); margin-top: 8px;">
      <div style="font-weight: 700; color: #fbbf24; font-size: 11.5px; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
        <span>☀️ SIMULADOR SOLAR (Lat: -27.40°)</span>
        <button id="btnPlaySun" onclick="toggleSunPlay()" style="background: #0284c7; border: none; color: white; padding: 2px 7px; border-radius: 4px; font-size: 10.5px; cursor: pointer; font-weight: 600;">▶️ Simular Dia</button>
      </div>

      <div class="slider-row">
        <span>📅 Estação / Data:</span>
        <span id="valSeason" class="slider-val" style="color: #fde047;">21/Dez (Solstício Verão)</span>
      </div>
      <input type="range" id="sliderDayOfYear" min="1" max="365" step="1" value="355" oninput="onSolarInputChange()">
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 3px; margin-top: 4px; margin-bottom: 8px;">
        <button class="btn btn-secondary" style="padding: 3px; font-size: 9.5px;" onclick="setSeasonPreset(355)">☀️ Solstício Verão</button>
        <button class="btn btn-secondary" style="padding: 3px; font-size: 9.5px;" onclick="setSeasonPreset(172)">❄️ Solstício Inverno</button>
        <button class="btn btn-secondary" style="padding: 3px; font-size: 9.5px;" onclick="setSeasonPreset(80)">🍂 Equinócio Outono</button>
        <button class="btn btn-secondary" style="padding: 3px; font-size: 9.5px;" onclick="setSeasonPreset(265)">🌸 Equinócio Primav.</button>
      </div>

      <div class="slider-row">
        <span>⏰ Horário Solar:</span>
        <span id="valSolarHour" class="slider-val" style="font-size: 12px; color: #38bdf8;">12:00</span>
      </div>
      <input type="range" id="sliderSolarHour" min="5.5" max="18.5" step="0.05" value="12.0" oninput="onSolarInputChange()">

      <div style="margin-top: 6px; padding-top: 5px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 10.5px; color: #94a3b8;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>Altitude Solar:</span><b id="valSolarAlt" style="color: #38bdf8;">86.0° (Zênite)</b>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>Azimute Solar:</span><b id="valSolarAz" style="color: #38bdf8;">0.0° (Norte)</b>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span>Projeção de Sombra:</span><b id="valShadowLength" style="color: #4ade80;">Mínima (0,07x)</b>
        </div>
      </div>
    </div>

    <!-- Opções Arquitetônicas do Salão 12x8m -->
    <div class="slider-box" style="border: 1px solid rgba(56, 189, 248, 0.4); background: rgba(15, 23, 42, 0.92); margin-top: 8px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
        <span style="font-weight: 700; color: #38bdf8; font-size: 11px;">🏛️ SALÃO 12×8m (36 MÓDULOS SOLARES)</span>
        <span id="badgeOpcao" style="font-size: 9.5px; font-weight: 700; background: #059669; color: white; padding: 2px 6px; border-radius: 4px;">OPÇÃO 1</span>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; margin-bottom: 6px;">
        <button class="btn btn-secondary btn-opt btn-opt-active" id="btnOpt1" onclick="setComplexOption(1)">🪵 1. Madeira</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt2" onclick="setComplexOption(2)">🏗️ 2. Metal 2 Águas</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt3" onclick="setComplexOption(3)">📐 3. 1 Água</button>
      </div>

      <div id="descOpcao" style="font-size: 10.5px; background: rgba(0,0,0,0.35); padding: 6px 8px; border-radius: 6px; color: #e2e8f0; line-height: 1.35; border-left: 3px solid #38bdf8;">
        <b>Opção 1: Madeira Rústica (Duas Águas)</b><br>
        Pilares de tora de eucalipto tratado, tesouras de madeira rústica e telhas cerâmicas terracota com 36 módulos solares fotovoltaicos (18 na água Sul + 18 na água Norte). 100% aberto sem paredes.
      </div>
    </div>

    <!-- Câmeras e Elementos -->
    <div class="btn-group">
      <button class="btn btn-secondary btn-toggle-active" id="btnBoundary" onclick="toggleBoundary()">🟡 Divisa do Sítio (18,60 ha) no Relevo</button>
      <button class="btn btn-secondary btn-toggle-active" id="btnSectors" onclick="toggleSectors()">🔷 Setores Solares (P1, P2, P3)</button>
      <button class="btn btn-secondary btn-toggle-active" id="btnSolar" onclick="toggleSolarPanels()" style="background: #1e3a8a; border-color: #3b82f6;">☀️ Ocultar Painéis Solares Solo</button>
      <button class="btn btn-secondary" onclick="focusOn('casa')">🏠 Focar na Casa do Sítio (200 m²)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('chales')">🏡 Focar nos Chalés 1 a 5 (22 m²)</button>
      <button class="btn btn-secondary" onclick="focusOn('p1')">🔎 Focar no Setor P1</button>
      <button class="btn btn-secondary" onclick="focusOn('p2')">🔎 Focar no Setor P2</button>
      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Geral da Propriedade</button>
      <button class="btn btn-accent" onclick="toggleWireframe()">⚡ Alternar Malha LiDAR 1,0 m (Wireframe)</button>
    </div>
  </div>

  <script>
    const widthM = {width_m:.2f};
    const depthM = {depth_m:.2f};
    const rows = {sub_rows};
    const cols = {sub_cols};
    const zMin = {z_min:.2f};
    const zRange = {z_range:.2f};

    const tables = {json.dumps(tables_data)};
    const salao = {json.dumps(salao_data)};
    const campo = {json.dumps(quadra_data)};
    const casa = {json.dumps(casa_data)};
    const chalesData = {json.dumps(chales_data)};

    const sitioCoords = {json.dumps(sitio_coords_3d)};
    const setoresCoords = {json.dumps(setores_coords)};

    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1.0, 5000);
    camera.position.set(-150, 480, 550);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: 'high-performance' }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.target.set(0, 150, 0);
    controls.update();

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x1e293b, 0.75);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff8e7, 1.25);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 50;
    sunLight.shadow.camera.far = 1600;
    sunLight.shadow.camera.left = -450;
    sunLight.shadow.camera.right = 450;
    sunLight.shadow.camera.top = 450;
    sunLight.shadow.camera.bottom = -450;
    scene.add(sunLight);
    scene.add(sunLight.target);

    // TERRENO 3D
    const b64Heights = "{b64_heights}";
    const binStr = atob(b64Heights);
    const u16Arr = new Uint16Array(binStr.length / 2);
    for (let i = 0; i < u16Arr.length; i++) {{
      u16Arr[i] = binStr.charCodeAt(i * 2) | (binStr.charCodeAt(i * 2 + 1) << 8);
    }}

    const geom = new THREE.PlaneGeometry(widthM, depthM, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);
    const pos = geom.attributes.position;

    // Terraplanagem suave dos platôs do Salão e Quadra
    const cos28 = Math.cos(THREE.MathUtils.degToRad(28.02));
    const sin28 = Math.sin(THREE.MathUtils.degToRad(28.02));

    for (let r = 0; r < rows; r++) {{
      for (let c = 0; c < cols; c++) {{
        const idx = r * cols + c;
        let h = (u16Arr[idx] / 65535.0) * zRange;
        const x = pos.getX(idx);
        const z = pos.getZ(idx);

        // Nivelamento do Salão
        const dxs = x - salao.x;
        const dzs = z - salao.z;
        const lxs = dxs * cos28 + dzs * sin28;
        const lzs = -dxs * sin28 + dzs * cos28;
        if (Math.abs(lxs) <= 7.2 && Math.abs(lzs) <= 5.2) {{
          h = salao.y - 0.02;
        }} else if (Math.abs(lxs) <= 10.5 && Math.abs(lzs) <= 8.5) {{
          const tx = Math.max(0.0, (Math.abs(lxs) - 7.2) / 3.3);
          const tz = Math.max(0.0, (Math.abs(lzs) - 5.2) / 3.3);
          const t = Math.min(1.0, Math.max(tx, tz));
          const s = 0.5 - 0.5 * Math.cos(Math.PI * t);
          h = (salao.y - 0.02) + s * (h - (salao.y - 0.02));
        }}

        // Nivelamento da Quadra de Areia
        const dxq = x - campo.x;
        const dzq = z - campo.z;
        const lxq = dxq * cos28 + dzq * sin28;
        const lzq = -dxq * sin28 + dzq * cos28;
        if (Math.abs(lxq) <= 12.0 && Math.abs(lzq) <= 7.0) {{
          h = campo.y - 0.02;
        }} else if (Math.abs(lxq) <= 16.0 && Math.abs(lzq) <= 11.0) {{
          const tx = Math.max(0.0, (Math.abs(lxq) - 12.0) / 4.0);
          const tz = Math.max(0.0, (Math.abs(lzq) - 7.0) / 4.0);
          const t = Math.min(1.0, Math.max(tx, tz));
          const s = 0.5 - 0.5 * Math.cos(Math.PI * t);
          h = (campo.y - 0.02) + s * (h - (campo.y - 0.02));
        }}

        pos.setY(idx, h);
      }}
    }}
    pos.needsUpdate = true;
    geom.computeVertexNormals();

    const matTerrain = new THREE.MeshStandardMaterial({{
      color: 0xffffff, roughness: 1.0, metalness: 0.0, side: THREE.DoubleSide
    }});
    const terrain = new THREE.Mesh(geom, matTerrain);
    terrain.receiveShadow = true;
    scene.add(terrain);

    // Carregamento da Textura Oficial SIGSC
    const texImg = new Image();
    texImg.src = "data:image/jpeg;base64,{b64_tex}";
    texImg.onload = function() {{
      const texture = new THREE.Texture(texImg);
      texture.encoding = THREE.sRGBEncoding;
      texture.generateMipmaps = true;
      texture.minFilter = THREE.LinearMipmapLinearFilter;
      texture.magFilter = THREE.LinearFilter;
      if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
        texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }}
      texture.needsUpdate = true;
      matTerrain.map = texture;
      matTerrain.needsUpdate = true;
      document.getElementById('loading').style.display = 'none';
      renderer.render(scene, camera);
    }};

    // DIVISA COMPLETA DO SÍTIO (18,60 ha) EM TUBO 3D CONTÍNUO
    const boundaryGroup = new THREE.Group();
    const boundaryPts = sitioCoords.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const boundaryCurve = new THREE.CatmullRomCurve3(boundaryPts, true);
    const boundaryTubeGeom = new THREE.TubeGeometry(boundaryCurve, Math.min(boundaryPts.length, 1600), 0.35, 6, true);
    const boundaryTubeMat = new THREE.MeshStandardMaterial({{
      color: 0xffea00, emissive: 0xffaa00, emissiveIntensity: 0.45, roughness: 0.3
    }});
    const boundaryTubeMesh = new THREE.Mesh(boundaryTubeGeom, boundaryTubeMat);
    boundaryGroup.add(boundaryTubeMesh);
    scene.add(boundaryGroup);

    // SETORES SOLARES P1, P2, P3
    const sectorsGroup = new THREE.Group();
    const sectorColors = {{
      p1: {{ color: 0x0284c7, emissive: 0x0369a1 }},
      p2: {{ color: 0x10b981, emissive: 0x059669 }},
      p3: {{ color: 0xf59e0b, emissive: 0xd97706 }}
    }};
    for (const [sKey, sPtsArr] of Object.entries(setoresCoords)) {{
      const sPoints = sPtsArr.map(p => new THREE.Vector3(p[0], p[1], p[2]));
      const sCurve = new THREE.CatmullRomCurve3(sPoints, true);
      const sTubeGeom = new THREE.TubeGeometry(sCurve, sPoints.length, 0.22, 5, true);
      const sMat = new THREE.MeshStandardMaterial({{
        color: sectorColors[sKey].color, emissive: sectorColors[sKey].emissive,
        emissiveIntensity: 0.4, roughness: 0.4
      }});
      sectorsGroup.add(new THREE.Mesh(sTubeGeom, sMat));
    }}
    scene.add(sectorsGroup);

    // MESAS SOLARES DE SOLO (233 mesas)
    const solarGroup = new THREE.Group();
    const tableGeom = new THREE.BoxGeometry(8.0, 0.22, 4.32);
    tableGeom.rotateX(-THREE.MathUtils.degToRad(20));
    const moduleMat = new THREE.MeshStandardMaterial({{ color: 0x1e3a8a, metalness: 0.8, roughness: 0.2 }});

    tables.forEach(t => {{
      const mMesh = new THREE.Mesh(tableGeom, moduleMat);
      mMesh.position.set(t.x, t.y + 1.2, t.z);
      mMesh.castShadow = true;
      solarGroup.add(mMesh);
    }});
    scene.add(solarGroup);

    // =========================================================================
    // EDIFICAÇÕES 3D (100% FIÉIS A visualizador_casa_arredores.html)
    // =========================================================================
    const complexGroup = new THREE.Group();
    scene.add(complexGroup);

    function createClayTileTextures() {{
      const w = 512, h = 512;
      const cDiff = document.createElement('canvas'); cDiff.width = w; cDiff.height = h;
      const ctx = cDiff.getContext('2d');
      const cBump = document.createElement('canvas'); cBump.width = w; cBump.height = h;
      const ctxB = cBump.getContext('2d');
      const colW = w / 12, rowH = h / 7;

      const imgD = ctx.createImageData(w, h); const d = imgD.data;
      const imgB = ctxB.createImageData(w, h); const b = imgB.data;

      for (let py = 0; py < h; py++) {{
        const rowIdx = Math.floor(py / rowH);
        const ry = (py % rowH) / rowH;
        const overlapShadow = ry < 0.11 ? (0.62 + 0.38 * (ry / 0.11)) : 1.0;
        const overlapBump = (1.0 - ry) * 35;

        for (let px = 0; px < w; px++) {{
          const colIdx = Math.floor(px / colW);
          const rx = (px % colW) / colW;
          const wave = Math.sin(rx * Math.PI * 2.0);
          const heightVal = (wave * 0.5 + 0.5);

          const tileSeed = Math.sin((rowIdx * 17 + colIdx * 31) * 12.9898) * 43758.5453;
          const tileVar = (tileSeed - Math.floor(tileSeed)) * 26 - 13;
          const grain = (Math.random() - 0.5) * 14;
          const shade = (0.76 + 0.30 * heightVal) * overlapShadow;

          const r = Math.min(255, Math.max(0, (178 + tileVar + grain) * shade));
          const g = Math.min(255, Math.max(0, (76 + tileVar * 0.45 + grain * 0.5) * shade));
          const bl = Math.min(255, Math.max(0, (32 + tileVar * 0.25 + grain * 0.3) * shade));

          const idx = (py * w + px) * 4;
          d[idx] = r; d[idx+1] = g; d[idx+2] = bl; d[idx+3] = 255;
          const bv = Math.min(255, Math.max(0, Math.floor(heightVal * 210 + overlapBump)));
          b[idx] = bv; b[idx+1] = bv; b[idx+2] = bv; b[idx+3] = 255;
        }}
      }}
      ctx.putImageData(imgD, 0, 0); ctxB.putImageData(imgB, 0, 0);

      const mapTex = new THREE.CanvasTexture(cDiff);
      mapTex.wrapS = THREE.RepeatWrapping; mapTex.wrapT = THREE.RepeatWrapping;
      const bumpTex = new THREE.CanvasTexture(cBump);
      bumpTex.wrapS = THREE.RepeatWrapping; bumpTex.wrapT = THREE.RepeatWrapping;
      return {{ mapTex, bumpTex }};
    }}

    const clayTextures = createClayTileTextures();

    // A) CASA DO SÍTIO (200 m², ALINHADA AOS KMZs 1 E 2)
    const casaGroup = new THREE.Group();
    casaGroup.position.set(casa.x, casa.y, casa.z);
    complexGroup.add(casaGroup);

    (function buildCasaSitioKMZ() {{
      const cxU = casa.cx_utm;
      const cyU = casa.cy_utm;
      const Rs = [663412.325, 6968630.679];
      const Rn = [663415.673, 6968642.764];
      const uE = 0.266982, uN = 0.963702;
      const nE = 0.963702, nN = -0.266982;
      const H_RIDGE = 4.60;
      const S_WEST = 0.34;
      const S_EAST = 0.235;

      function roofMetrics(e, n) {{
        const along = (e - Rs[0]) * uE + (n - Rs[1]) * uN;
        const perp = (e - Rs[0]) * nE + (n - Rs[1]) * nN;
        const h = (perp <= 0) ? (H_RIDGE - S_WEST * Math.abs(perp)) : (H_RIDGE - S_EAST * perp);
        return {{ lx: e - cxU, lz: -(n - cyU), along: along, perp: perp, h: h }};
      }}

      // Vértices Exatos telhado1.kmz (Ala Oeste)
      const t1UTM = [
        [663408.675, 6968631.318], Rs, Rn,
        [663411.758, 6968643.518], [663408.972, 6968633.456], [663407.240, 6968633.914]
      ];
      const t1P = t1UTM.map(pt => roofMetrics(pt[0], pt[1]));

      const t1Geom = new THREE.BufferGeometry();
      const t1Pos = [], t1Uvs = [];
      const t1Tris = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]];
      t1Tris.forEach(tri => {{
        tri.forEach(vi => {{
          t1Pos.push(t1P[vi].lx, t1P[vi].h, t1P[vi].lz);
          t1Uvs.push(t1P[vi].along * 0.22, t1P[vi].perp * 0.28);
        }});
      }});
      t1Geom.setAttribute('position', new THREE.Float32BufferAttribute(t1Pos, 3));
      t1Geom.setAttribute('uv', new THREE.Float32BufferAttribute(t1Uvs, 2));
      t1Geom.computeVertexNormals();

      const roofMatOeste = new THREE.MeshStandardMaterial({{
        map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.045,
        roughness: 0.72, metalness: 0.08, side: THREE.DoubleSide
      }});
      const t1Mesh = new THREE.Mesh(t1Geom, roofMatOeste);
      t1Mesh.castShadow = true;
      casaGroup.add(t1Mesh);

      // Vértices Exatos telhado2.kmz (Ala Leste)
      const t2UTM = [
        Rs, [663420.916, 6968628.307], [663424.264, 6968640.392], Rn
      ];
      const t2P = t2UTM.map(pt => roofMetrics(pt[0], pt[1]));
      const t2Geom = new THREE.BufferGeometry();
      const t2Pos = [], t2Uvs = [];
      [[0, 1, 2], [0, 2, 3]].forEach(tri => {{
        tri.forEach(vi => {{
          t2Pos.push(t2P[vi].lx, t2P[vi].h, t2P[vi].lz);
          t2Uvs.push(t2P[vi].along * 0.22, t2P[vi].perp * 0.28);
        }});
      }});
      t2Geom.setAttribute('position', new THREE.Float32BufferAttribute(t2Pos, 3));
      t2Geom.setAttribute('uv', new THREE.Float32BufferAttribute(t2Uvs, 2));
      t2Geom.computeVertexNormals();

      const roofMatLeste = new THREE.MeshStandardMaterial({{
        map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.045,
        roughness: 0.72, metalness: 0.08, side: THREE.DoubleSide
      }});
      const t2Mesh = new THREE.Mesh(t2Geom, roofMatLeste);
      t2Mesh.castShadow = true;
      casaGroup.add(t2Mesh);

      // Cumeeira Central
      const pRs = roofMetrics(Rs[0], Rs[1]);
      const pRn = roofMetrics(Rn[0], Rn[1]);
      const cumLineGeom = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(pRs.lx, pRs.h + 0.03, pRs.lz),
        new THREE.Vector3(pRn.lx, pRn.h + 0.03, pRn.lz)
      ]);
      casaGroup.add(new THREE.Line(cumLineGeom, new THREE.LineBasicMaterial({{ color: 0x7c2d12, linewidth: 3 }})));

      // Paredes e Piso
      const wallPts = [
        [-7.3, -4.5], [-3.18, -5.82], [5.0, -8.19], [8.76, 3.89],
        [0.17, 6.26], [-3.74, 7.02], [-6.53, -3.04], [-8.26, -2.59]
      ];
      const floorShape = new THREE.Shape();
      wallPts.forEach((p, idx) => {{
        if (idx === 0) floorShape.moveTo(p[0], -p[1]);
        else floorShape.lineTo(p[0], -p[1]);
      }});
      const floorGeom = new THREE.ShapeGeometry(floorShape);
      floorGeom.rotateX(Math.PI / 2);
      const floorMesh = new THREE.Mesh(floorGeom, new THREE.MeshStandardMaterial({{ color: 0x9a3412, roughness: 0.8 }}));
      floorMesh.position.y = 0.05;
      casaGroup.add(floorMesh);

      const wallMat = new THREE.MeshStandardMaterial({{ color: 0xf8fafc, roughness: 0.85 }});
      const wallGeom = new THREE.BufferGeometry();
      const wallVerts = [];
      for (let i = 0; i < wallPts.length; i++) {{
        const cur = wallPts[i];
        const nxt = wallPts[(i + 1) % wallPts.length];
        const h1 = 2.80, h2 = 2.80;
        wallVerts.push(
          cur[0], 0, cur[1],  nxt[0], 0, nxt[1],  nxt[0], h2, nxt[1],
          cur[0], 0, cur[1],  nxt[0], h2, nxt[1], cur[0], h1, cur[1]
        );
      }}
      wallGeom.setAttribute('position', new THREE.Float32BufferAttribute(wallVerts, 3));
      wallGeom.computeVertexNormals();
      casaGroup.add(new THREE.Mesh(wallGeom, wallMat));
    }})();

    // B) SALÃO 12x8m COM 36 MÓDULOS SOLARES
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salao.x, salao.y, salao.z);
    salaoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(salaoGroup);

    const matFloorConcrete = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.6 }});
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.0, 0.25, 8.0), matFloorConcrete);
    salaoFloor.position.y = 0.125;
    salaoGroup.add(salaoFloor);

    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), matFloorConcrete);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      salaoGroup.add(step);
    }}

    function createSalaoSolarRow(numCols = 9, modW = 1.134, modL = 1.95) {{
      const rowGroup = new THREE.Group();
      const gap = 0.03;
      const totalW = numCols * modW + (numCols - 1) * gap;
      const startX = -totalW / 2 + modW / 2;
      for (let c = 0; c < numCols; c++) {{
        const x = startX + c * (modW + gap);
        const cell = new THREE.Mesh(new THREE.BoxGeometry(modW - 0.035, 0.04, modL - 0.035), moduleMat);
        cell.position.set(x, 0.045, 0);
        cell.castShadow = true;
        rowGroup.add(cell);
      }}
      return rowGroup;
    }}

    const opt1Group = new THREE.Group();
    const opt2Group = new THREE.Group();
    const opt3Group = new THREE.Group();
    salaoGroup.add(opt1Group, opt2Group, opt3Group);

    // OPÇÃO 1: MADEIRA RÚSTICA (2 Águas com 36 módulos solares)
    const rusticWoodMat = new THREE.MeshStandardMaterial({{ color: 0x4a2e18, roughness: 0.85 }});
    const tileCeramicMat = new THREE.MeshStandardMaterial({{
      map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.05, roughness: 0.72
    }});

    const pilarPositions = [
      [-5.7, 1.85, -3.7], [0, 1.85, -3.7], [5.7, 1.85, -3.7],
      [-5.7, 1.85, 3.7],  [0, 1.85, 3.7],  [5.7, 1.85, 3.7]
    ];
    pilarPositions.forEach(p => {{
      const pMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 3.6, 12), rusticWoodMat);
      pMesh.position.set(p[0], p[1], p[2]);
      pMesh.castShadow = true;
      opt1Group.add(pMesh);
    }});

    const viga1 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga1.rotation.z = Math.PI / 2; viga1.position.set(0, 3.65, -3.7);
    const viga2 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga2.rotation.z = Math.PI / 2; viga2.position.set(0, 3.65, 3.7);
    opt1Group.add(viga1, viga2);

    const roofWoodBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.10, 4.6), tileCeramicMat);
    roofWoodBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofWoodBack.position.set(0, 4.35, -2.15);
    const roofWoodFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.10, 4.6), tileCeramicMat);
    roofWoodFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofWoodFront.position.set(0, 4.35, 2.15);
    opt1Group.add(roofWoodBack, roofWoodFront);

    // 36 Painéis Solares (18 na água Frontal + 18 na água Posterior)
    const solarBackOpt1 = new THREE.Group();
    solarBackOpt1.rotation.x = -THREE.MathUtils.degToRad(18.0);
    solarBackOpt1.position.set(0, 4.35, -2.15);
    const r1Back1 = createSalaoSolarRow(9, 1.134, 1.95); r1Back1.position.set(0, 0.08, -1.05);
    const r2Back1 = createSalaoSolarRow(9, 1.134, 1.95); r2Back1.position.set(0, 0.08, 1.05);
    solarBackOpt1.add(r1Back1, r2Back1);

    const solarFrontOpt1 = new THREE.Group();
    solarFrontOpt1.rotation.x = THREE.MathUtils.degToRad(18.0);
    solarFrontOpt1.position.set(0, 4.35, 2.15);
    const r1Front1 = createSalaoSolarRow(9, 1.134, 1.95); r1Front1.position.set(0, 0.08, -1.05);
    const r2Front1 = createSalaoSolarRow(9, 1.134, 1.95); r2Front1.position.set(0, 0.08, 1.05);
    solarFrontOpt1.add(r1Front1, r2Front1);
    opt1Group.add(solarBackOpt1, solarFrontOpt1);

    // OPÇÃO 2: ESTRUTURA METÁLICA
    const steelDarkMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }});
    const panelSandwichMat = new THREE.MeshStandardMaterial({{ color: 0x475569, metalness: 0.5, roughness: 0.4 }});
    pilarPositions.forEach(p => {{
      const pSteel = new THREE.Mesh(new THREE.BoxGeometry(0.20, 3.6, 0.20), steelDarkMat);
      pSteel.position.set(p[0], p[1], p[2]);
      opt2Group.add(pSteel);
    }});
    const roofSteelBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofSteelBack.position.set(0, 4.35, -2.15);
    const roofSteelFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofSteelFront.position.set(0, 4.35, 2.15);
    opt2Group.add(roofSteelBack, roofSteelFront);

    // OPÇÃO 3: 1 ÁGUA NO DECLIVE
    [-5.7, 0, 5.7].forEach(x => {{
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.1, 0.2), steelDarkMat);
      pBack.position.set(x, 2.05, -3.7); opt3Group.add(pBack);
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.9, 0.2), steelDarkMat);
      pFront.position.set(x, 1.45, 3.7); opt3Group.add(pFront);
    }});
    const roofMono = new THREE.Mesh(new THREE.BoxGeometry(13.0, 0.12, 9.4), panelSandwichMat);
    roofMono.rotation.x = THREE.MathUtils.degToRad(9.3);
    roofMono.position.set(0, 4.25, 0);
    opt3Group.add(roofMono);

    opt1Group.visible = true;
    opt2Group.visible = false;
    opt3Group.visible = false;

    // C) QUADRA DE AREIA 22x12m (TELAS H=6m; LADO OESTE ABERTO PARA A CASA)
    const campoGroup = new THREE.Group();
    campoGroup.position.set(campo.x, campo.y, campo.z);
    campoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(campoGroup);

    const sandMat = new THREE.MeshStandardMaterial({{ color: 0xfde047, roughness: 0.95 }});
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.30, 12.0), sandMat);
    sandMesh.position.y = 0.15;
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    const bordaMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const bordaMesh = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.40, 12.3), bordaMat);
    bordaMesh.position.y = 0.20;
    campoGroup.add(bordaMesh);

    const postMatQuadra = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, metalness: 0.7, roughness: 0.3 }});
    const quadraPostPositions = [
      [-11, -6], [-5.5, -6], [0, -6], [5.5, -6], [11, -6],
      [-11, 6], [-5.5, 6], [0, 6], [5.5, 6], [11, 6]
    ];
    quadraPostPositions.forEach(p => {{
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, 6.0, 8), postMatQuadra);
      pole.position.set(p[0], 3.0, p[1]);
      campoGroup.add(pole);
    }});

    const telasGroup = new THREE.Group();
    campoGroup.add(telasGroup);

    const telaMat = new THREE.MeshBasicMaterial({{
      color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.38, side: THREE.DoubleSide
    }});

    const telaSul = new THREE.Mesh(new THREE.PlaneGeometry(22.0, 6.0, 22, 6), telaMat);
    telaSul.position.set(0, 3.0, -6.0);
    telasGroup.add(telaSul);

    const telaNorte = new THREE.Mesh(new THREE.PlaneGeometry(22.0, 6.0, 22, 6), telaMat);
    telaNorte.position.set(0, 3.0, 6.0);
    telasGroup.add(telaNorte);

    const telaLeste = new THREE.Mesh(new THREE.PlaneGeometry(12.0, 6.0, 12, 6), telaMat);
    telaLeste.position.set(11.0, 3.0, 0);
    telaLeste.rotation.y = Math.PI / 2;
    telasGroup.add(telaLeste);

    const cableMat = new THREE.LineBasicMaterial({{ color: 0xe2e8f0, linewidth: 2 }});
    const cablePts = [
      new THREE.Vector3(-11, 6.0, -6), new THREE.Vector3(11, 6.0, -6),
      new THREE.Vector3(11, 6.0, 6), new THREE.Vector3(-11, 6.0, 6)
    ];
    telasGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts), cableMat));

    const netGameMat = new THREE.MeshBasicMaterial({{ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.75 }});
    const net = new THREE.Mesh(new THREE.PlaneGeometry(8.5, 1.0), netGameMat);
    net.position.set(0, 2.2, 0);
    net.rotation.y = Math.PI / 2;
    campoGroup.add(net);

    // D) CHALÉS 1 A 5 (22 m² CADA, CHALÉS 4 E 5 GIRADOS PARA A CASA)
    const chaleWallMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const chaleRoofMat = new THREE.MeshStandardMaterial({{ color: 0x9a3412, roughness: 0.7 }});
    const chaleGlassMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.2, metalness: 0.8 }});
    const chalePilarMat = new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.9 }});
    const chaleDeckMat = new THREE.MeshStandardMaterial({{ color: 0x5c2d16, roughness: 0.75 }});

    chalesData.forEach(c => {{
      const cGroup = new THREE.Group();
      cGroup.position.set(c.x, c.y, c.z);
      if (c.id === 4 || c.id === 5) {{
        cGroup.rotation.y = Math.atan2(casa.x - c.x, casa.z - c.z);
      }} else {{
        cGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
      }}

      const pilotiCoords = [
        [-2.4, -1.8], [0.0, -1.8], [2.4, -1.8],
        [-2.4, 1.8],  [0.0, 1.8],  [2.4, 1.8]
      ];
      pilotiCoords.forEach(pt => {{
        const pMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.16, 4.0, 8), chalePilarMat);
        pMesh.position.set(pt[0], -1.9, pt[1]);
        pMesh.castShadow = true;
        cGroup.add(pMesh);
      }});

      const baseDeck = new THREE.Mesh(new THREE.BoxGeometry(5.50, 0.20, 4.00), chaleDeckMat);
      baseDeck.position.set(0, 0.10, 0);
      cGroup.add(baseDeck);

      const body = new THREE.Mesh(new THREE.BoxGeometry(5.40, 2.70, 2.80), chaleWallMat);
      body.position.set(0, 1.55, -0.55);
      cGroup.add(body);

      const rGeom = new THREE.BufferGeometry();
      const rPts = [
        -2.90, 2.75, -2.20,  -2.90, 2.75, 2.20,   0.00, 4.10, 2.20,
        -2.90, 2.75, -2.20,   0.00, 4.10, 2.20,   0.00, 4.10, -2.20,
         0.00, 4.10, -2.20,   0.00, 4.10, 2.20,   2.90, 2.75, 2.20,
         0.00, 4.10, -2.20,   2.90, 2.75, 2.20,   2.90, 2.75, -2.20
      ];
      rGeom.setAttribute('position', new THREE.Float32BufferAttribute(rPts, 3));
      rGeom.computeVertexNormals();
      const rMesh = new THREE.Mesh(rGeom, chaleRoofMat);
      cGroup.add(rMesh);

      const railMat = new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.5 }});
      const railFront = new THREE.Mesh(new THREE.BoxGeometry(5.40, 0.90, 0.06), railMat);
      railFront.position.set(0, 0.65, 1.95);
      const railL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railL.position.set(-2.67, 0.65, 1.35);
      const railR = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railR.position.set(2.67, 0.65, 1.35);
      cGroup.add(railFront, railL, railR);

      const win = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.8), chaleGlassMat);
      win.position.set(0, 1.45, 0.86);
      cGroup.add(win);

      complexGroup.add(cGroup);
    }});

    // ESFERA SOLAR NO CÉU
    const sunSphereGeom = new THREE.SphereGeometry(24, 16, 16);
    const sunSphereMat = new THREE.MeshBasicMaterial({{ color: 0xfff08a }});
    const sunSphere = new THREE.Mesh(sunSphereGeom, sunSphereMat);
    scene.add(sunSphere);

    // CÁLCULOS ASTRONÔMICOS DO SIMULADOR SOLAR
    const LAT_RAD = -27.395 * Math.PI / 180.0;
    const LON_DEG = -49.347;
    const R_SUN_ORBIT = 1800;

    function computeSunAngles(dayOfYear, hourOfDay) {{
      const b = (360.0 / 365.0) * (dayOfYear - 81) * Math.PI / 180.0;
      const decl = 23.45 * Math.PI / 180.0 * Math.sin(b);
      const eot = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
      const timeOffset = eot + 4.0 * (LON_DEG - (-45.0));
      const trueSolarTime = hourOfDay + timeOffset / 60.0;
      const omega = (trueSolarTime - 12.0) * 15.0 * Math.PI / 180.0;

      const vEast = -Math.cos(decl) * Math.sin(omega);
      const vNorth = -Math.sin(LAT_RAD) * Math.cos(decl) * Math.cos(omega) + Math.cos(LAT_RAD) * Math.sin(decl);
      const vUp = Math.cos(LAT_RAD) * Math.cos(decl) * Math.cos(omega) + Math.sin(LAT_RAD) * Math.sin(decl);

      const alpha = Math.asin(Math.max(-1.0, Math.min(1.0, vUp)));
      let azDeg = Math.atan2(vEast, vNorth) * 180.0 / Math.PI;
      if (azDeg < 0) azDeg += 360.0;

      return {{
        alphaRad: alpha, alphaDeg: alpha * 180.0 / Math.PI,
        gammaDeg: azDeg, vEast: vEast, vNorth: vNorth, vUp: vUp
      }};
    }}

    const monthNames = [
      {{ name: 'Jan', days: 31 }}, {{ name: 'Fev', days: 28 }}, {{ name: 'Mar', days: 31 }},
      {{ name: 'Abr', days: 30 }}, {{ name: 'Mai', days: 31 }}, {{ name: 'Jun', days: 30 }},
      {{ name: 'Jul', days: 31 }}, {{ name: 'Ago', days: 31 }}, {{ name: 'Set', days: 30 }},
      {{ name: 'Out', days: 31 }}, {{ name: 'Nov', days: 30 }}, {{ name: 'Dez', days: 31 }}
    ];

    function dayOfYearToDateStr(d) {{
      let rem = d;
      for (let m = 0; m < 12; m++) {{
        if (rem <= monthNames[m].days) return rem + ' de ' + monthNames[m].name;
        rem -= monthNames[m].days;
      }}
      return '31 de Dez';
    }}

    function getCardinalDirection(deg) {{
      const dirs = ['N', 'NNE', 'NE', 'ENE', 'L', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO', 'N'];
      return dirs[Math.round(deg / 22.5)];
    }}

    let isSunPlaying = false;
    function toggleSunPlay() {{
      isSunPlaying = !isSunPlaying;
      const btn = document.getElementById('btnPlaySun');
      btn.textContent = isSunPlaying ? '⏸️ Pausar' : '▶️ Simular Dia';
      btn.style.background = isSunPlaying ? '#e11d48' : '#0284c7';
    }}

    function updateSunSimulation() {{
      const day = parseFloat(document.getElementById('sliderDayOfYear').value);
      const hour = parseFloat(document.getElementById('sliderSolarHour').value);
      const sun = computeSunAngles(day, hour);

      const hFloor = Math.floor(hour);
      const mFloor = Math.floor((hour - hFloor) * 60);
      document.getElementById('valSolarHour').innerText = String(hFloor).padStart(2, '0') + ':' + String(mFloor).padStart(2, '0');
      document.getElementById('valSeason').innerText = dayOfYearToDateStr(day);

      document.getElementById('valSolarAlt').innerText = sun.alphaDeg.toFixed(1) + '°' + (sun.alphaDeg > 80 ? ' (Zênite)' : (sun.alphaDeg <= 0 ? ' (Abaixo Horizon.)' : ''));
      document.getElementById('valSolarAz').innerText = sun.gammaDeg.toFixed(1) + '° (' + getCardinalDirection(sun.gammaDeg) + ')';

      const shadowMult = sun.alphaRad > 0.05 ? (1.0 / Math.tan(sun.alphaRad)).toFixed(2) + 'x' : 'Infinita / Noite';
      document.getElementById('valShadowLength').innerText = shadowMult;

      if (sun.alphaRad > 0.0) {{
        sunLight.intensity = Math.min(1.4, Math.sin(sun.alphaRad) * 1.5 + 0.1);
        sunLight.position.set(sun.vEast * R_SUN_ORBIT, sun.vUp * R_SUN_ORBIT, -sun.vNorth * R_SUN_ORBIT);
        sunSphere.position.copy(sunLight.position);
        sunSphere.visible = true;
      }} else {{
        sunLight.intensity = 0.0;
        sunSphere.visible = false;
      }}
    }}

    window.onSolarInputChange = function() {{ updateSunSimulation(); }};
    window.setSeasonPreset = function(day) {{
      document.getElementById('sliderDayOfYear').value = day;
      updateSunSimulation();
    }};

    // CONTROLE DE OPÇÕES DO SALÃO
    const optionDescriptions = {{
      1: "<b>Opção 1: Madeira Rústica (Duas Águas)</b><br>Pilares de tora de eucalipto tratado, tesouras de madeira rústica e telhas cerâmicas terracota com 36 módulos solares fotovoltaicos (18 na água Sul + 18 na água Norte). 100% aberto sem paredes.",
      2: "<b>Opção 2: Estrutura Metálica (Duas Águas)</b><br>Pilares e vigas em perfil de aço escuro com telhas termoacústicas sandwich e 36 módulos solares fotovoltaicos.",
      3: "<b>Opção 3: Telhado 1 Água (Declive da Encosta)</b><br>Cobertura mono-inclinada descendo no sentido da encosta e quadra de areia."
    }};

    window.setComplexOption = function(opt) {{
      opt1Group.visible = (opt === 1);
      opt2Group.visible = (opt === 2);
      opt3Group.visible = (opt === 3);

      for (let i = 1; i <= 3; i++) {{
        const btn = document.getElementById('btnOpt' + i);
        if (btn) btn.classList.toggle('btn-opt-active', i === opt);
      }}

      document.getElementById('badgeOpcao').innerText = 'OPÇÃO ' + opt;
      document.getElementById('descOpcao').innerHTML = optionDescriptions[opt];
    }};

    // CÂMERAS E NAVEGAÇÃO
    window.focusOn = function(target) {{
      let tCam, tTarget;
      if (target === 'casa') {{
        tCam = new THREE.Vector3(casa.x + 32, casa.y + 18, casa.z + 36);
        tTarget = new THREE.Vector3(casa.x, casa.y + 2.5, casa.z);
      }} else if (target === 'salao') {{
        tCam = new THREE.Vector3(salao.x + 26, salao.y + 14, salao.z + 24);
        tTarget = new THREE.Vector3(salao.x, salao.y + 2.5, salao.z);
      }} else if (target === 'chales') {{
        tCam = new THREE.Vector3(salao.x + 45, salao.y + 30, salao.z - 50);
        tTarget = new THREE.Vector3(salao.x + 5, salao.y + 4.0, salao.z - 25);
      }} else if (target === 'p1') {{
        const t0 = tables[0];
        tCam = new THREE.Vector3(t0.x - 60, t0.y + 70, t0.z + 120);
        tTarget = new THREE.Vector3(t0.x + 30, t0.y + 10, t0.z);
      }} else if (target === 'p2') {{
        const t2 = tables.find(t => t.setor === 'P2') || tables[0];
        tCam = new THREE.Vector3(t2.x - 70, t2.y + 70, t2.z + 100);
        tTarget = new THREE.Vector3(t2.x + 20, t2.y, t2.z);
      }} else if (target === 'p3') {{
        const t3 = tables.find(t => t.setor === 'P3') || tables[0];
        tCam = new THREE.Vector3(t3.x - 50, t3.y + 50, t3.z + 80);
        tTarget = new THREE.Vector3(t3.x, t3.y, t3.z);
      }} else {{
        tCam = new THREE.Vector3(0, 480, 580);
        tTarget = new THREE.Vector3(0, 150, 0);
      }}

      animateCamera(tCam, tTarget, 1000);
    }};

    function animateCamera(targetPos, targetLookAt, duration) {{
      const startPos = camera.position.clone();
      const startLookAt = controls.target.clone();
      const startTime = performance.now();

      function step(now) {{
        const progress = Math.min((now - startTime) / duration, 1.0);
        const ease = 0.5 - 0.5 * Math.cos(progress * Math.PI);
        camera.position.lerpVectors(startPos, targetPos, ease);
        controls.target.lerpVectors(startLookAt, targetLookAt, ease);
        controls.update();
        if (progress < 1.0) requestAnimationFrame(step);
      }}
      requestAnimationFrame(step);
    }}

    let isWire = false;
    window.toggleWireframe = function() {{ isWire = !isWire; matTerrain.wireframe = isWire; }};
    let showBoundary = true;
    window.toggleBoundary = function() {{ showBoundary = !showBoundary; boundaryGroup.visible = showBoundary; }};
    let showSectors = true;
    window.toggleSectors = function() {{ showSectors = !showSectors; sectorsGroup.visible = showSectors; }};
    let showSolar = true;
    window.toggleSolarPanels = function() {{ showSolar = !showSolar; solarGroup.visible = showSolar; }};

    window.addEventListener('resize', onWindowResize, false);
    function onWindowResize() {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }}

    updateSunSimulation();

    let lastTime = performance.now();
    function animate(now) {{
      requestAnimationFrame(animate);
      const dt = (now - lastTime) / 1000.0;
      lastTime = now;

      if (isSunPlaying) {{
        const sliderH = document.getElementById('sliderSolarHour');
        let h = parseFloat(sliderH.value) + dt * 0.75;
        if (h > 18.5) h = 5.5;
        sliderH.value = h.toFixed(2);
        updateSunSimulation();
      }}

      controls.update();
      renderer.render(scene, camera);
    }}
    animate(performance.now());
  </script>
</body>
</html>
"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_code)
    print(f"6. Sucesso! visualizador_3d_sitio.html salvo ({os.path.getsize(HTML_OUT):,} bytes)")

    shutil.copyfile(HTML_OUT, INDEX_OUT)
    print(f"7. index.html atualizado ({os.path.getsize(INDEX_OUT):,} bytes)")
    print("================================================================================")

if __name__ == "__main__":
    main()
