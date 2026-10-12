#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: atualizar_sitio_completo_sigsc.py
Objetivo:
1. Gerar visualizador_3d_sitio.html e espelhar em index.html com a malha estendida 100% SIGSC oficial
   (1.250 m x 1.350 m = 168,7 ha) contendo toda a divisa do sítio (18,60 ha) contínua e sem cortes.
2. Incorporar as edificações EXATAS de visualizador_casa_arredores.html com as posições originais:
   - Casa do Sítio: 200 m², alinhada com KMZ telhado1 e telhado2, cota 540,95m no terreno natural.
   - Salão de Festas: 12x8m, 100% aberto, sem estacas perfurando o telhado, 36 módulos solares (ambas as águas).
   - Quadra de Areia: 22x12m, mourões de madeira, telas H=6m nos lados Sul, Norte e Leste; lado Oeste aberto para a casa; SEM postes pretos.
   - Posição do Salão (lx=49.59, lz=-22.91) e Quadra (lx=68.93, lz=-10.32) 100% separadas (23,08 m de distância) sem sobreposição!
   - Chalés 1 a 5: 22 m² cada sobre pilotis de eucalipto, chalés 4 e 5 rotacionados voltados para a Casa do Sítio.
3. Preservar 100% do Simulador Solar Astronômico (sliders, órbita solar, azimute/elevação, telemetria e sombras).
4. NÃO ALTERAR visualizador_casa_arredores.html.
"""

import os
import json
import base64
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon
from PIL import Image

SOLAR_DIR = r"C:\Users\haas\github\solar"
MDT_PATH = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Estendida.tif")
ORTO_PATH = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Area_Estendida.tif")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")
CASA_HTML_PATH = os.path.join(SOLAR_DIR, "visualizador_casa_arredores.html")
OUTPUT_HTML = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")
INDEX_HTML = os.path.join(SOLAR_DIR, "index.html")

def main():
    print("=" * 80)
    print("GERANDO VISUALIZADOR 3D COM TODA A DIVISÓRIA USANDO SIGSC OFICIAL")
    print("=" * 80)

    # 1. Leitura do MDT SIGSC
    print("1. Lendo MDT LiDAR 1,0 m SIGSC da área estendida...")
    with rasterio.open(MDT_PATH) as src_m:
        elev_raw = src_m.read(1)
        bounds = src_m.bounds
        res = src_m.res
        meta = src_m.meta

    elev_clean = np.where((elev_raw < -100) | (elev_raw > 2000) | np.isnan(elev_raw), 500.0, elev_raw)
    z_min = float(np.min(elev_clean))
    z_max = float(np.max(elev_clean))
    z_range = z_max - z_min

    width_m = float(bounds.right - bounds.left)
    depth_m = float(bounds.top - bounds.bottom)
    cx = float((bounds.left + bounds.right) / 2.0)
    cy = float((bounds.bottom + bounds.top) / 2.0)
    rows, cols = elev_clean.shape

    step = 2
    sub_elev = elev_clean[::step, ::step]
    sub_rows, sub_cols = sub_elev.shape

    norm_h = np.clip((sub_elev - z_min) / z_range, 0.0, 1.0)
    u16_h = (norm_h * 65535.0).astype(np.uint16)
    b64_heights = base64.b64encode(u16_h.tobytes()).decode('ascii')

    print(f"   Dimensões do Terreno: {width_m:.1f} m x {depth_m:.1f} m (Grade nativa: {cols} x {rows})")
    print(f"   Centro do Modelo 3D: E {cx:.2f}, N {cy:.2f}")
    print(f"   Cotas SIGSC: Mínima = {z_min:.2f} m | Máxima = {z_max:.2f} m | Desnível = {z_range:.2f} m")
    print(f"   Malha WebGL: {sub_cols} x {sub_rows} = {sub_cols * sub_rows:,} vértices")

    # 2. Codificação da Ortofoto SIGSC
    print("2. Codificando textura Ortofoto SIGSC 0,39 m em alta definição...")
    with rasterio.open(ORTO_PATH) as src_o:
        r = src_o.read(1)
        g = src_o.read(2)
        b = src_o.read(3)

    rgb = np.stack([r, g, b], axis=-1)
    img_pil = Image.fromarray(rgb)
    img_resized = img_pil.resize((2500, 2700), Image.Resampling.LANCZOS)
    img_byte_arr = os.path.join(SOLAR_DIR, "_tmp_orto_sigsc.jpg")
    img_resized.save(img_byte_arr, format='JPEG', quality=86, optimize=True)

    with open(img_byte_arr, "rb") as f_img:
        b64_orto = base64.b64encode(f_img.read()).decode('ascii')
    if os.path.exists(img_byte_arr):
        os.remove(img_byte_arr)
    print(f"   Textura SIGSC: 2500x2700 px ({len(b64_orto) / 1024 / 1024:.2f} MB em Base64)")

    # 3. Divisória Completa do Sítio
    print("3. Amostrando divisa completa do sítio (18,60 ha) sobre o relevo...")
    def sample_poly_3d(poly, step=1.5, dz=0.85):
        ext = poly.exterior
        total_len = ext.length
        num_pts = max(10, int(total_len / step))
        pts = []
        for i in range(num_pts):
            dist = i * step
            pt = ext.interpolate(dist)
            col = int((pt.x - bounds.left) / res[0])
            row = int((bounds.top - pt.y) / res[1])
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

    # 4. Mesas Fotovoltaicas de Solo
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

    # 5. Extração Fiel das Edificações de visualizador_casa_arredores.html
    print("5. Extraindo edificações e dados originais de visualizador_casa_arredores.html...")
    with open(CASA_HTML_PATH, "r", encoding="utf-8") as f_ref:
        ref_lines = f_ref.read().split('\n')

    block_data = '\n'.join(ref_lines[185:212])
    block_textures = '\n'.join(ref_lines[318:380])
    block_buildings = '\n'.join(ref_lines[380:1022])

    full_building_js = f"""
    // =========================================================================
    // DADOS E CONSTRUÇÕES EXTRAÍDAS DIRETAMENTE DE visualizador_casa_arredores.html
    // =========================================================================
    const edifGroup = new THREE.Group();
    // Offset geodésico milimétrico para ancorar perfeitamente as edificações no SIGSC estendido:
    // CX_UTM = 663400.00, CY_UTM = 6968630.00, Z_MIN_DRONE = 446.2713
    // cx = {cx:.2f}, cy = {cy:.2f}, z_min = {z_min:.2f}
    const EDIF_OFFSET_X = {663400.00 - cx:.2f};      // -125.00 m
    const EDIF_OFFSET_Y = {446.2713 - z_min:.4f};    // +67.9013 m
    const EDIF_OFFSET_Z = {-(6968630.00 - cy):.2f};   // -5.00 m
    edifGroup.position.set(EDIF_OFFSET_X, EDIF_OFFSET_Y, EDIF_OFFSET_Z);
    scene.add(edifGroup);

{block_data}

{block_textures}

{block_buildings}
"""

    # 6. Montagem do HTML completo com Three.js e Simulador Solar Astronômico
    print("6. Gerando HTML unificado com toda a divisória SIGSC e simulador solar...")
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
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}

    #compass-rose {{
      position: absolute; bottom: 20px; right: 20px; width: 68px; height: 68px;
      background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255,255,255,0.15);
      border-radius: 50%; display: flex; align-items: center; justify-content: center;
      font-weight: 800; font-size: 13px; color: #ef4444; pointer-events: none;
      box-shadow: 0 4px 14px rgba(0,0,0,0.4);
    }}
  </style>

  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="loading">
    <div class="spinner"></div>
    Carregando Terreno 3D SIGSC Estendido...<br>
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
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão de Festas (12×8 m)</button>
      <button class="btn btn-secondary" onclick="focusOn('quadra')">🏐 Focar na Quadra de Areia (22×12 m)</button>
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
    const sitioCoords = {json.dumps(sitio_coords_3d)};
    const setoresCoords = {json.dumps(setores_coords)};

    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1.0, 5000);
    // Posicionamento inicial focado na Casa do Sítio e complexo
    camera.position.set(-109.50 + 45, 162.58 + 35, -11.50 + 50);

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
    controls.target.set(-109.50, 162.58 + 2.0, -11.50);
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
    sunLight.target.position.set(-109.50, 162.58, -11.50);
    scene.add(sunLight);
    scene.add(sunLight.target);

    // TERRENO 3D COM MDT LIDAR E ORTOFOTO
    const b64Heights = "{b64_heights}";
    const binStr = atob(b64Heights);
    const u16Arr = new Uint16Array(binStr.length / 2);
    for (let i = 0; i < u16Arr.length; i++) {{
      u16Arr[i] = binStr.charCodeAt(i * 2) | (binStr.charCodeAt(i * 2 + 1) << 8);
    }}

    const geom = new THREE.PlaneGeometry(widthM, depthM, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);
    const pos = geom.attributes.position;
    for (let i = 0; i < pos.count; i++) {{
      pos.setY(i, (u16Arr[i] / 65535.0) * zRange);
    }}
    geom.computeVertexNormals();

    const texLoader = new THREE.TextureLoader();
    const ortoTex = texLoader.load("data:image/jpeg;base64,{b64_orto}", () => {{
      document.getElementById('loading').style.display = 'none';
    }});
    ortoTex.wrapS = THREE.ClampToEdgeWrapping;
    ortoTex.wrapT = THREE.ClampToEdgeWrapping;
    ortoTex.anisotropy = renderer.capabilities.getMaxAnisotropy();

    const terrainMat = new THREE.MeshStandardMaterial({{
      map: ortoTex, roughness: 0.88, metalness: 0.05
    }});
    const terrainMesh = new THREE.Mesh(geom, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // LINHA DE DIVISA DO SÍTIO NO RELEVO (18,60 ha COMPLETA E CONTÍNUA)
    const sitioPts = sitioCoords.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    sitioPts.push(sitioPts[0]);
    const sitioCurve = new THREE.CatmullRomCurve3(sitioPts);
    const tubeGeom = new THREE.TubeGeometry(sitioCurve, sitioPts.length * 2, 0.40, 6, true);
    const tubeMat = new THREE.MeshBasicMaterial({{ color: 0xfacc15 }});
    const lineSitio = new THREE.Mesh(tubeGeom, tubeMat);
    scene.add(lineSitio);

    // SETORES SOLARES (P1, P2, P3)
    const lineSectors = [];
    const sectorColors = {{ p1: 0x38bdf8, p2: 0x4ade80, p3: 0xf43f5e }};
    for (const [sId, sPts] of Object.entries(setoresCoords)) {{
      const vPts = sPts.map(p => new THREE.Vector3(p[0], p[1], p[2]));
      vPts.push(vPts[0]);
      const sCurve = new THREE.CatmullRomCurve3(vPts);
      const sTube = new THREE.TubeGeometry(sCurve, vPts.length * 2, 0.30, 6, true);
      const sMesh = new THREE.Mesh(sTube, new THREE.MeshBasicMaterial({{ color: sectorColors[sId] }}));
      scene.add(sMesh);
      lineSectors.push(sMesh);
    }}

    // MESAS FOTOVOLTAICAS DE SOLO (233 mesas)
    const solarTablesGroup = new THREE.Group();
    scene.add(solarTablesGroup);

    const moduleMat = new THREE.MeshStandardMaterial({{
      color: 0x0f172a, roughness: 0.15, metalness: 0.85
    }});
    const structMat = new THREE.MeshStandardMaterial({{
      color: 0x94a3b8, roughness: 0.5, metalness: 0.7
    }});

    const singleTableGeom = new THREE.Group();
    const panelBox = new THREE.Mesh(new THREE.BoxGeometry(4.40, 0.08, 1.95), moduleMat);
    panelBox.rotation.x = THREE.MathUtils.degToRad(-15.0);
    panelBox.position.y = 1.25;
    panelBox.castShadow = true;
    singleTableGeom.add(panelBox);

    const post1 = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.3), structMat);
    post1.position.set(-1.8, 0.65, 0.3); post1.castShadow = true;
    const post2 = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.04, 1.3), structMat);
    post2.position.set(1.8, 0.65, 0.3); post2.castShadow = true;
    singleTableGeom.add(post1, post2);

    tables.forEach(t => {{
      const inst = singleTableGeom.clone();
      inst.position.set(t.x, t.y, t.z);
      solarTablesGroup.add(inst);
    }});

    /* BUILDING_CODE_PLACEHOLDER */

    // ESFERA SOLAR E TRAÇADO ASTRONÔMICO
    const sunSphereGeom = new THREE.SphereGeometry(18, 16, 16);
    const sunSphereMat = new THREE.MeshBasicMaterial({{ color: 0xfff07c }});
    const sunSphere = new THREE.Mesh(sunSphereGeom, sunSphereMat);
    scene.add(sunSphere);

    const R_SUN_ORBIT = 1100.0;
    const LAT_RAD = -27.40 * Math.PI / 180.0;

    function computeSunAngles(dayOfYear, hour) {{
      const b = (2.0 * Math.PI / 365.0) * (dayOfYear - 1);
      const delta = 0.006918 - 0.399912 * Math.cos(b) + 0.070257 * Math.sin(b)
                    - 0.006758 * Math.cos(2 * b) + 0.000907 * Math.sin(2 * b)
                    - 0.002697 * Math.cos(3 * b) + 0.00148 * Math.sin(3 * b);

      const omega = (hour - 12.0) * 15.0 * Math.PI / 180.0;

      const sinAlpha = Math.sin(LAT_RAD) * Math.sin(delta) + Math.cos(LAT_RAD) * Math.cos(delta) * Math.cos(omega);
      const alpha = Math.asin(Math.max(-1.0, Math.min(1.0, sinAlpha)));

      let gamma = 0.0;
      if (Math.abs(Math.cos(alpha)) > 1e-5) {{
        const cosGamma = (Math.sin(delta) - Math.sin(LAT_RAD) * Math.sin(alpha)) / (Math.cos(LAT_RAD) * Math.cos(alpha));
        gamma = Math.acos(Math.max(-1.0, Math.min(1.0, cosGamma)));
        if (Math.sin(omega) > 0) gamma = 2.0 * Math.PI - gamma;
      }}

      const vUp = Math.sin(alpha);
      const vNorth = Math.cos(alpha) * Math.cos(gamma);
      const vEast = Math.cos(alpha) * Math.sin(gamma);

      let azDeg = (gamma * 180.0 / Math.PI + 180.0) % 360.0;
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
    window.toggleSunPlay = function() {{
      isSunPlaying = !isSunPlaying;
      const btn = document.getElementById('btnPlaySun');
      btn.textContent = isSunPlaying ? '⏸️ Pausar' : '▶️ Simular Dia';
      btn.style.background = isSunPlaying ? '#e11d48' : '#0284c7';
    }};

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
        sunLight.position.set(sun.vEast * R_SUN_ORBIT - 109.50, sun.vUp * R_SUN_ORBIT, -sun.vNorth * R_SUN_ORBIT - 11.50);
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

    // CONTROLE DE OPÇÕES DO SALÃO 12x8m
    const optionDescriptions = {{
      1: "<b>Opção 1: Madeira Rústica (Duas Águas)</b><br>Pilares de tora de eucalipto tratado, tesouras de madeira rústica e telhas cerâmicas terracota com 36 módulos solares fotovoltaicos (18 na água Sul + 18 na água Norte). 100% aberto sem paredes.",
      2: "<b>Opção 2: Estrutura Metálica (Duas Águas)</b><br>Pilares e vigas em perfil de aço escuro com telhas termoacústicas sandwich e 36 módulos solares fotovoltaicos.",
      3: "<b>Opção 3: Telhado 1 Água (Declive da Encosta)</b><br>Cobertura mono-inclinada descendo no sentido da encosta e quadra de areia."
    }};

    window.setComplexOption = function(opt) {{
      if (typeof optGroup1 !== 'undefined') optGroup1.visible = (opt === 1);
      if (typeof optGroup2 !== 'undefined') optGroup2.visible = (opt === 2);
      if (typeof optGroup3 !== 'undefined') optGroup3.visible = (opt === 3);

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
      // Posicionamento global rigoroso das edificações no espaço SIGSC:
      // Casa: (-109.50, 162.58, -11.50)
      // Salão: (-75.41, 168.73, -27.91)
      // Quadra: (-56.07, 168.88, -15.32)
      if (target === 'casa') {{
        tCam = new THREE.Vector3(-109.50 + 32, 162.58 + 20, -11.50 + 36);
        tTarget = new THREE.Vector3(-109.50, 162.58 + 2.5, -11.50);
      }} else if (target === 'salao') {{
        tCam = new THREE.Vector3(-75.41 + 24, 168.73 + 14, -27.91 + 20);
        tTarget = new THREE.Vector3(-75.41, 168.73 + 2.5, -27.91);
      }} else if (target === 'quadra' || target === 'campo') {{
        tCam = new THREE.Vector3(-56.07 + 25, 168.88 + 16, -15.32 + 22);
        tTarget = new THREE.Vector3(-56.07, 168.88 + 2.0, -15.32);
      }} else if (target === 'chales') {{
        tCam = new THREE.Vector3(-75.41 + 42, 168.73 + 28, -27.91 - 48);
        tTarget = new THREE.Vector3(-75.41 + 5, 168.73 + 2.0, -27.91 - 25);
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

    window.toggleBoundary = function() {{
      lineSitio.visible = !lineSitio.visible;
      document.getElementById('btnBoundary').classList.toggle('btn-toggle-active', lineSitio.visible);
    }};

    window.toggleSectors = function() {{
      const vis = !lineSectors[0].visible;
      lineSectors.forEach(l => l.visible = vis);
      document.getElementById('btnSectors').classList.toggle('btn-toggle-active', vis);
    }};

    window.toggleSolarPanels = function() {{
      solarTablesGroup.visible = !solarTablesGroup.visible;
      const btn = document.getElementById('btnSolar');
      btn.innerText = solarTablesGroup.visible ? "☀️ Ocultar Painéis Solares Solo" : "☀️ Exibir Painéis Solares Solo";
      btn.classList.toggle('btn-toggle-active', solarTablesGroup.visible);
    }};

    window.toggleWireframe = function() {{
      terrainMat.wireframe = !terrainMat.wireframe;
    }};

    // LOOP DE ANIMAÇÃO
    function animate() {{
      requestAnimationFrame(animate);

      if (isSunPlaying) {{
        const sHour = document.getElementById('sliderSolarHour');
        let curH = parseFloat(sHour.value) + 0.035;
        if (curH > 18.5) curH = 5.5;
        sHour.value = curH.toFixed(2);
        updateSunSimulation();
      }}

      controls.update();
      renderer.render(scene, camera);
    }}

    updateSunSimulation();
    animate();

    window.addEventListener('resize', () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});
  </script>
</body>
</html>
"""

    html_code = html_code.replace("/* BUILDING_CODE_PLACEHOLDER */", full_building_js)

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f_out:
        f_out.write(html_code)
    print(f"7. Sucesso! visualizador_3d_sitio.html salvo ({os.path.getsize(OUTPUT_HTML):,} bytes)")

    with open(INDEX_HTML, "w", encoding="utf-8") as f_idx:
        f_idx.write(html_code)
    print(f"8. index.html atualizado ({os.path.getsize(INDEX_HTML):,} bytes)")
    print("=" * 80)

if __name__ == "__main__":
    main()
