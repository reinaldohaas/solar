#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o Visualizador 3D Geral do Sítio das Andorinhas (visualizador_3d_sitio.html e index.html):
1. Área ESTENDIDA (1250 m x 1350 m = 168 ha) cobrindo 100% da divisa do sítio (18,60 ha) com folga
2. Relevo 3D gerado a partir do MDT LiDAR 1,0 m Oficial SIGSC (MDT_SIGSC_Area_Drone_Estendida.tif)
3. Textura de Alta Resolução da Ortofoto Oficial SIGSC 0,39 m (Ortofoto_SIGSC_Area_Estendida.tif)
4. Linha Perimetral da Divisa do Sítio modelada em Tubo 3D contínuo sobre o relevo natural
5. Linhas de Divisão dos Setores Solares (P1, P2, P3) e 233 Mesas Fotovoltaicas de Solo (2,46 MWp)
6. Modelos de Engenharia Idênticos ao visualizador_casa_arredores.html (o padrão oficial):
   - Casa do Sítio (200 m², telhados 1 e 2 KMZ, cota 540,95 m, relevo natural preservado)
   - Salão de Festas (12×8m = 96 m², 100% aberto, sem estacas, 3 opções, usina solar 36 módulos em ambos os lados)
   - Quadra de Areia (22×12m, telas Sul, Leste e Norte H=6m, lado Oeste aberto para a casa, sem refletores pretos)
   - Chalés 1 a 5 (22 m² cada, sobre pilotis no terreno, Chalés 4 e 5 girados na direção da Casa do Sítio)
7. Exporta para visualizador_3d_sitio.html e copia para index.html
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
    print("GERANDO VISUALIZADOR 3D GERAL ESTENDIDO: SÍTIO DAS ANDORINHAS")
    print("================================================================================")

    # 1. Leitura do MDT LiDAR 1,0 m Estendido
    print("1. Lendo MDT LiDAR SIGSC Estendido (1250 m x 1350 m)...")
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
    print(f"   Dimensões do Terreno: {width_m:.1f} m x {depth_m:.1f} m (Grade: {cols} x {rows})")
    print(f"   Centro do Modelo 3D: E {cx:.2f}, N {cy:.2f}")
    print(f"   Cotas SIGSC: Mínima = {z_min:.2f} m | Máxima = {z_max:.2f} m | Desnível = {z_range:.2f} m")

    elev_clean = np.where(np.isnan(elev), z_min, elev)
    
    # Subamostragem leve do grid para 625x675 (step 2m) para performance ultra-fluida a 60fps
    step_grid = 2
    elev_sub = elev_clean[::step_grid, ::step_grid]
    sub_rows, sub_cols = elev_sub.shape
    print(f"   Malha WebGL Otimizada: {sub_cols} x {sub_rows} = {sub_cols*sub_rows:,} vértices")

    uint16_arr = np.round(((elev_sub - z_min) / z_range) * 65535).astype(np.uint16)
    b64_heights = base64.b64encode(uint16_arr.tobytes()).decode('ascii')

    # 2. Leitura da Ortofoto Oficial SIGSC
    print("2. Processando Textura Ortofoto SIGSC de Alta Fidelidade...")
    tex_w = 2500
    tex_h = int(round(tex_w * depth_m / width_m))
    with rasterio.open(ORTO_TIF) as src_o:
        rgb = src_o.read([1, 2, 3], out_shape=(3, tex_h, tex_w), resampling=Resampling.bilinear)
    
    img = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=84)
    b64_tex = base64.b64encode(buf.getvalue()).decode('ascii')
    print(f"   Textura JPEG: {tex_w}x{tex_h} px ({len(b64_tex)/1024/1024:.2f} MB em Base64)")

    # 3. Amostragem 3D da Divisa do Sítio (18,60 ha) e Setores Solares
    print("3. Amostrando contorno perimetral do Sítio e Setores Solares sobre o relevo...")
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
    print(f"   Divisa do Sítio (18,60 ha): {len(sitio_coords_3d)} vértices contínuos sobre o relevo")

    setores_coords = {}
    for s in ['p1', 'p2', 'p3']:
        gdf_s = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{s}')
        poly_s = gdf_s.union_all().convex_hull.buffer(3.5)
        setores_coords[s] = sample_poly_3d(poly_s, step=2.0, dz=0.60)
        print(f"   Divisão do Setor {s.upper()}: {len(setores_coords[s])} vértices")

    # 4. Mesas Fotovoltaicas de Solo P1, P2, P3
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
    print(f"   Total de Mesas UFV Solo: {len(tables_data)}")

    # 5. Coordenadas Locais das Edificações no Modelo Estendido
    rot_rad = -0.489038 # -28.02°

    casa_utm = (663415.50, 6968636.50)
    cota_casa = 540.95
    casa_data = {
        'utm': casa_utm,
        'cota': cota_casa,
        'lx': round(casa_utm[0] - cx, 2),
        'lz': round(-(casa_utm[1] - cy), 2),
        'base_y': round(cota_casa - z_min, 2),
        'cx_utm': casa_utm[0],
        'cy_utm': casa_utm[1]
    }

    salao_utm = (663445.60, 6968642.80)
    cota_salao = 547.10
    salao_data = {
        'utm': salao_utm,
        'cota': cota_salao,
        'lx': round(salao_utm[0] - cx, 2),
        'lz': round(-(salao_utm[1] - cy), 2),
        'base_y': round(cota_salao - z_min, 2),
        'rot_rad': rot_rad
    }

    quadra_utm = (663456.88, 6968636.85)
    cota_quadra = 547.25
    quadra_data = {
        'utm': quadra_utm,
        'cota': cota_quadra,
        'lx': round(quadra_utm[0] - cx, 2),
        'lz': round(-(quadra_utm[1] - cy), 2),
        'base_y': round(cota_quadra - z_min, 2),
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
            'lx': round(e - cx, 2),
            'lz': round(-(n - cy), 2),
            'base_y': round(c['cota'] - z_min, 2)
        })

    # 6. Montagem do HTML com Three.js
    print("5. Montando código HTML completo e responsivo...")
    html_code = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D Geral — Sítio das Andorinhas (100% SIGSC LiDAR 1,0 m)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      overflow: hidden;
      background: #090d16;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #f8fafc;
    }}
    #canvas-container {{ width: 100vw; height: 100vh; }}

    #panel {{
      position: absolute; top: 16px; left: 16px; width: 380px;
      background: rgba(13, 19, 33, 0.94); color: #f8fafc; padding: 18px;
      border-radius: 14px; box-shadow: 0 16px 45px rgba(0,0,0,0.75);
      border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(16px);
      z-index: 10; max-height: calc(100vh - 32px); overflow-y: auto;
    }}
    h1 {{ font-size: 16px; font-weight: 700; color: #38bdf8; margin-bottom: 3px; display: flex; align-items: center; gap: 8px; }}
    .subtitle {{ font-size: 11px; color: #94a3b8; margin-bottom: 10px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }}
    .badge {{
      font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
      background: #0284c7; color: #fff; text-transform: uppercase; letter-spacing: 0.4px;
    }}
    .badge-sigsc {{ background: #059669; }}
    .badge-scale {{ background: #d97706; }}

    .stat-row {{
      display: flex; justify-content: space-between; font-size: 11.5px;
      padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.06);
    }}
    .stat-lbl {{ color: #94a3b8; }}
    .stat-val {{ font-weight: 600; color: #4ade80; }}

    .section-title {{
      margin-top: 13px; margin-bottom: 6px; font-size: 10.5px; font-weight: 800;
      color: #cbd5e1; text-transform: uppercase; letter-spacing: 0.6px;
      display: flex; justify-content: space-between; align-items: center;
    }}

    .btn-group {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 5px; }}
    .btn {{
      background: rgba(255,255,255,0.07); color: #f8fafc; border: 1px solid rgba(255,255,255,0.14);
      padding: 7px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer;
      transition: all 0.2s ease; text-align: center;
    }}
    .btn:hover {{ background: #0284c7; border-color: #38bdf8; }}
    .btn.active {{ background: #0284c7; border-color: #38bdf8; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }}
    .btn-full {{ grid-column: span 2; }}

    .toggle-row {{
      display: flex; align-items: center; justify-content: space-between;
      font-size: 11px; margin-top: 6px; color: #cbd5e1;
    }}
    .toggle-row input {{ cursor: pointer; accent-color: #38bdf8; }}

    .slider-box {{
      margin-top: 9px; padding: 10px; background: rgba(16, 185, 129, 0.08);
      border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.25);
    }}
    .slider-row {{
      display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;
      color: #cbd5e1; margin-bottom: 4px;
    }}
    .slider-val {{ color: #34d399; font-weight: 800; }}
    input[type=range] {{ width: 100%; accent-color: #10b981; cursor: pointer; }}

    #loading {{
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(13, 19, 33, 0.95); color: #38bdf8; padding: 24px 36px;
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
    Renderizando Sítio das Andorinhas em 3D...<br>
    <span style="font-size: 11px; color: #94a3b8;">MDT LiDAR 1,0 m & Ortofoto SIGSC (Área Estendida 168 ha)</span>
  </div>

  <div id="canvas-container"></div>

  <div id="panel">
    <h1>🌐 Sítio das Andorinhas 3D</h1>
    <div class="subtitle">Modelo Georreferenciado Completo (Área Estendida 168 ha)</div>

    <div class="badges">
      <span class="badge badge-sigsc">MDT LiDAR 1,0 m</span>
      <span class="badge badge-sigsc">Ortofoto SIGSC 0,39 m</span>
      <span class="badge badge-scale">Escala 1:1 Nativa</span>
    </div>

    <!-- Estatísticas Oficiais -->
    <div class="stat-row">
      <span class="stat-lbl">Área da Propriedade:</span>
      <span class="stat-val">18,60 ha (186.016 m²)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Área 3D Renderizada:</span>
      <span class="stat-val">{width_m:.0f} m × {depth_m:.0f} m (168,7 ha)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Cota Casa do Sítio:</span>
      <span class="stat-val">540,95 m (200 m² no terreno natural)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Cota Salão de Festas:</span>
      <span class="stat-val">547,10 m (12×8m = 96 m²)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Cota Quadra de Areia:</span>
      <span class="stat-val">547,25 m (22×12m = 264 m²)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Chalés 1 a 5 (Pilotis):</span>
      <span class="stat-val">22 m² cada (547,07 m a 551,91 m)</span>
    </div>
    <div class="stat-row">
      <span class="stat-lbl">Usinas de Solo P1, P2, P3:</span>
      <span class="stat-val">233 mesas | 2,46 MWp</span>
    </div>

    <!-- Link para Visualizador Detalhado -->
    <a href="visualizador_casa_arredores.html" target="_blank" class="btn btn-full" style="margin-top: 10px; background: #0284c7; color: #fff; text-decoration: none; padding: 8px 12px; border-radius: 6px; font-weight: 700; border: 1px solid #38bdf8; display: flex; align-items: center; justify-content: center; gap: 6px;">
      🏡 Abrir Visualizador Detalhado (Casa do Sítio & Arredores)
    </a>

    <!-- Opções do Salão -->
    <div class="section-title">
      <span>Cobertura Salão 12×8m (Usina 36 Módulos)</span>
      <span style="font-size: 9.5px; color: #f59e0b;">100% Aberto</span>
    </div>
    <div class="btn-group">
      <button class="btn active" id="btnOpt1" onclick="setSalaoOption(1)">🪵 1. Madeira Rústica</button>
      <button class="btn" id="btnOpt2" onclick="setSalaoOption(2)">🏗️ 2. Metálica 2 Águas</button>
      <button class="btn btn-full" id="btnOpt3" onclick="setSalaoOption(3)">📐 3. Telhado 1 Água (Declive Encosta)</button>
    </div>

    <!-- Câmeras Rápidas -->
    <div class="section-title">Câmeras & Navegação 3D</div>
    <div class="btn-group">
      <button class="btn" onclick="goToView('casa')">🏠 Casa do Sítio</button>
      <button class="btn" onclick="goToView('salao')">🏛️ Salão & Quadra</button>
      <button class="btn" onclick="goToView('chales')">🏡 Chalés 1 a 5</button>
      <button class="btn" onclick="goToView('quadra')">🏐 Na Quadra</button>
      <button class="btn" onclick="goToView('p1')">☀️ Setor P1</button>
      <button class="btn" onclick="goToView('p2')">☀️ Setor P2</button>
      <button class="btn" onclick="goToView('p3')">☀️ Setor P3</button>
      <button class="btn btn-full" onclick="goToView('panoramica')">🌐 Panorâmica Geral da Propriedade</button>
    </div>

    <!-- Camadas & Ferramentas -->
    <div class="section-title">Camadas & Elementos</div>
    <div class="toggle-row">
      <span>🟡 Divisa do Sítio (18,60 ha) no Relevo</span>
      <input type="checkbox" id="chk-boundary" checked onchange="toggleBoundary(this.checked)">
    </div>
    <div class="toggle-row">
      <span>🔷 Limites Setores Solares (P1, P2, P3)</span>
      <input type="checkbox" id="chk-sectors" checked onchange="toggleSectors(this.checked)">
    </div>
    <div class="toggle-row">
      <span>☀️ Usinas Fotovoltaicas de Solo (233 mesas)</span>
      <input type="checkbox" id="chk-solar" checked onchange="toggleSolar(this.checked)">
    </div>
    <div class="toggle-row">
      <span>🏛️ Edificações 3D (Casa, Salão, Quadra, Chalés)</span>
      <input type="checkbox" id="chk-edif" checked onchange="toggleEdif(this.checked)">
    </div>
    <div class="toggle-row">
      <span>🏐 Telas / Redes da Quadra (H=6m)</span>
      <input type="checkbox" id="chk-telas" checked onchange="toggleTelas(this.checked)">
    </div>
    <div class="toggle-row">
      <span>Malha de Relevo (Wireframe 1m)</span>
      <input type="checkbox" id="chk-wire" onchange="toggleWire(this.checked)">
    </div>

    <!-- Controle de Escala Z -->
    <div class="slider-box">
      <div class="slider-row">
        <span>Exagero Vertical (Z):</span>
        <span class="slider-val" id="lblZScale">1.00x (Real 1:1)</span>
      </div>
      <input type="range" id="sliderZScale" min="0.5" max="3.0" step="0.05" value="1.0" oninput="setZScale(this.value)">
      <div class="btn-group" style="margin-top: 6px;">
        <button class="btn" onclick="setZScalePreset(1.0)">1.0x Real</button>
        <button class="btn" onclick="setZScalePreset(1.25)">1.25x</button>
        <button class="btn" onclick="setZScalePreset(1.5)">1.5x</button>
        <button class="btn" onclick="setZScalePreset(2.0)">2.0x</button>
      </div>
    </div>
  </div>

  <script>
    // =========================================================================
    // 1. CONSTANTES E COORDENADAS GEORREFERENCIADAS
    // =========================================================================
    const WIDTH_M = {width_m:.2f};
    const DEPTH_M = {depth_m:.2f};
    const COLS = {sub_cols};
    const ROWS = {sub_rows};
    const Z_MIN = {z_min:.2f};
    const Z_MAX = {z_max:.2f};
    const Z_RANGE = {z_range:.2f};
    const CX_UTM = {cx:.2f};
    const CY_UTM = {cy:.2f};

    const casaData = {json.dumps(casa_data)};
    const salaoData = {json.dumps(salao_data)};
    const quadraData = {json.dumps(quadra_data)};
    const chalesData = {json.dumps(chales_data)};

    const sitioCoords = {json.dumps(sitio_coords_3d)};
    const setoresCoords = {json.dumps(setores_coords)};
    const tables = {json.dumps(tables_data)};

    // =========================================================================
    // 2. INICIALIZAÇÃO DA CENA THREE.JS
    // =========================================================================
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1.0, 5000);
    camera.position.set(casaData.lx + 150, casaData.base_y + 110, casaData.lz + 160);

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
    controls.target.set(casaData.lx, casaData.base_y + 10, casaData.lz);
    controls.update();

    // Iluminação Solar
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.85);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff8e7, 1.35);
    sunLight.position.set(350, casaData.base_y + 400, 300);
    sunLight.target.position.set(casaData.lx, casaData.base_y, casaData.lz);
    scene.add(sunLight.target);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 50;
    sunLight.shadow.camera.far = 1200;
    sunLight.shadow.camera.left = -400;
    sunLight.shadow.camera.right = 400;
    sunLight.shadow.camera.top = 400;
    sunLight.shadow.camera.bottom = -400;
    scene.add(sunLight);

    // =========================================================================
    // 3. TERRENO 3D COM MDT LIDAR 1,0 m & TEXTURA ORTOFOTO SIGSC
    // =========================================================================
    const b64Heights = "{b64_heights}";
    const binStr = atob(b64Heights);
    const u16Arr = new Uint16Array(binStr.length / 2);
    for (let i = 0; i < u16Arr.length; i++) {{
      u16Arr[i] = binStr.charCodeAt(i * 2) | (binStr.charCodeAt(i * 2 + 1) << 8);
    }}

    const geom = new THREE.PlaneGeometry(WIDTH_M, DEPTH_M, COLS - 1, ROWS - 1);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    const baseElevations = new Float32Array(pos.count);
    for (let r = 0; r < ROWS; r++) {{
      for (let c = 0; c < COLS; c++) {{
        const vertexIdx = r * COLS + c;
        const normH = u16Arr[vertexIdx] / 65535.0;
        const realH = normH * Z_RANGE;
        baseElevations[vertexIdx] = realH;
        pos.setY(vertexIdx, realH);
      }}
    }}
    pos.needsUpdate = true;
    geom.computeVertexNormals();

    const terrainMat = new THREE.MeshStandardMaterial({{
      color: 0xffffff,
      roughness: 0.95,
      metalness: 0.05,
      side: THREE.DoubleSide
    }});
    const terrainMesh = new THREE.Mesh(geom, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // Wireframe opcional
    const wireMat = new THREE.MeshBasicMaterial({{ color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.22 }});
    const wireMesh = new THREE.Mesh(geom, wireMat);
    wireMesh.visible = false;
    scene.add(wireMesh);

    // Carregamento da Textura Base64
    const texImg = new Image();
    texImg.src = "data:image/jpeg;base64,{b64_tex}";
    texImg.onload = function() {{
      const tex = new THREE.Texture(texImg);
      tex.encoding = THREE.sRGBEncoding;
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.magFilter = THREE.LinearFilter;
      if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
        tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }}
      tex.needsUpdate = true;
      terrainMat.map = tex;
      terrainMat.needsUpdate = true;
      document.getElementById('loading').style.display = 'none';
      renderer.render(scene, camera);
    }};

    // =========================================================================
    // 4. DIVISA DO SÍTIO (18,60 ha) E SETORES SOLARES SOBRE O RELEVO
    // =========================================================================
    const boundaryGroup = new THREE.Group();
    const boundaryPts = sitioCoords.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    const boundaryCurve = new THREE.CatmullRomCurve3(boundaryPts, true);
    const boundaryTubeGeom = new THREE.TubeGeometry(boundaryCurve, Math.min(boundaryPts.length, 1600), 0.35, 6, true);
    const boundaryTubeMat = new THREE.MeshStandardMaterial({{
      color: 0xffea00, emissive: 0xffaa00, emissiveIntensity: 0.45, roughness: 0.3
    }});
    boundaryGroup.add(new THREE.Mesh(boundaryTubeGeom, boundaryTubeMat));
    scene.add(boundaryGroup);

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

    // Mesas Fotovoltaicas de Solo (233 mesas)
    const solarGroup = new THREE.Group();
    const tableGeom = new THREE.BoxGeometry(8.0, 0.20, 4.32);
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
    // 5. EDIFICAÇÕES 3D (PADRÃO OFICIAL: CASA, SALÃO, QUADRA, CHALÉS)
    // =========================================================================
    const edifGroup = new THREE.Group();
    scene.add(edifGroup);

    // Textura de Telhas Coloniais Cerâmicas
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

    // A) CASA DO SÍTIO (200 m² - Telhados 1 e 2 KMZ Alinhados, Sem Montículo)
    const casaGroup = new THREE.Group();
    casaGroup.position.set(casaData.lx, casaData.base_y, casaData.lz);
    edifGroup.add(casaGroup);

    (function buildCasaSitioKMZ() {{
      const cxU = casaData.cx_utm;
      const cyU = casaData.cy_utm;
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
      const t1Tris = [
        [0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]
      ];
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

    // B) SALÃO DE FESTAS 12x8m (Usina Solar 36 Módulos em Ambos os Lados)
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salaoData.lx, salaoData.base_y, salaoData.lz);
    salaoGroup.rotation.y = -salaoData.rot_rad;
    edifGroup.add(salaoGroup);

    const salaoFloorMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.6 }});
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.0, 0.25, 8.0), salaoFloorMat);
    salaoFloor.position.y = 0.125;
    salaoGroup.add(salaoFloor);

    // Escada frontal
    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), salaoFloorMat);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      salaoGroup.add(step);
    }}

    // Opções de Cobertura
    const optGroup1 = new THREE.Group();
    const optGroup2 = new THREE.Group();
    const optGroup3 = new THREE.Group();
    salaoGroup.add(optGroup1, optGroup2, optGroup3);

    // Função de criação de fileira solar
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

    // OPÇÃO 1: MADEIRA RÚSTICA 2 ÁGUAS
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
      optGroup1.add(pMesh);
    }});

    const viga1 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga1.rotation.z = Math.PI / 2; viga1.position.set(0, 3.65, -3.7);
    const viga2 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga2.rotation.z = Math.PI / 2; viga2.position.set(0, 3.65, 3.7);
    optGroup1.add(viga1, viga2);

    const roofWoodBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.10, 4.6), tileCeramicMat);
    roofWoodBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofWoodBack.position.set(0, 4.35, -2.15);
    const roofWoodFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.10, 4.6), tileCeramicMat);
    roofWoodFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofWoodFront.position.set(0, 4.35, 2.15);
    optGroup1.add(roofWoodBack, roofWoodFront);

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
    optGroup1.add(solarBackOpt1, solarFrontOpt1);

    // OPÇÃO 2: ESTRUTURA METÁLICA
    const steelDarkMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }});
    const panelSandwichMat = new THREE.MeshStandardMaterial({{ color: 0x475569, metalness: 0.5, roughness: 0.4 }});
    pilarPositions.forEach(p => {{
      const pSteel = new THREE.Mesh(new THREE.BoxGeometry(0.20, 3.6, 0.20), steelDarkMat);
      pSteel.position.set(p[0], p[1], p[2]);
      optGroup2.add(pSteel);
    }});
    const roofSteelBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofSteelBack.position.set(0, 4.35, -2.15);
    const roofSteelFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofSteelFront.position.set(0, 4.35, 2.15);
    optGroup2.add(roofSteelBack, roofSteelFront);

    // OPÇÃO 3: 1 ÁGUA NO DECLIVE
    [-5.7, 0, 5.7].forEach(x => {{
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.1, 0.2), steelDarkMat);
      pBack.position.set(x, 2.05, -3.7); optGroup3.add(pBack);
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.9, 0.2), steelDarkMat);
      pFront.position.set(x, 1.45, 3.7); optGroup3.add(pFront);
    }});
    const roofMono = new THREE.Mesh(new THREE.BoxGeometry(13.0, 0.12, 9.4), panelSandwichMat);
    roofMono.rotation.x = THREE.MathUtils.degToRad(9.3);
    roofMono.position.set(0, 4.25, 0);
    optGroup3.add(roofMono);

    optGroup1.visible = true;
    optGroup2.visible = false;
    optGroup3.visible = false;

    // C) QUADRA DE AREIA 22x12m (Telas Sul, Leste, Norte H=6m; Oeste Aberto)
    const quadraGroup = new THREE.Group();
    quadraGroup.position.set(quadraData.lx, quadraData.base_y, quadraData.lz);
    quadraGroup.rotation.y = -quadraData.rot_rad;
    edifGroup.add(quadraGroup);

    const sandMat = new THREE.MeshStandardMaterial({{ color: 0xfde047, roughness: 0.95 }});
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.30, 12.0), sandMat);
    sandMesh.position.y = 0.15;
    quadraGroup.add(sandMesh);

    const bordaMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const bordaMesh = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.40, 12.3), bordaMat);
    bordaMesh.position.y = 0.20;
    quadraGroup.add(bordaMesh);

    // 10 Postes Metálicos de 6m
    const postMat = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, metalness: 0.7, roughness: 0.3 }});
    const quadraPostPositions = [
      [-11, -6], [-5.5, -6], [0, -6], [5.5, -6], [11, -6],
      [-11, 6], [-5.5, 6], [0, 6], [5.5, 6], [11, 6]
    ];
    quadraPostPositions.forEach(p => {{
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, 6.0, 8), postMat);
      pole.position.set(p[0], 3.0, p[1]);
      quadraGroup.add(pole);
    }});

    // Telas H = 6,00 m (Lado Oeste Aberto para a Casa)
    const telasGroup = new THREE.Group();
    quadraGroup.add(telasGroup);

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

    // Cabos de aço superiores
    const cableMat = new THREE.LineBasicMaterial({{ color: 0xe2e8f0, linewidth: 2 }});
    const cablePts = [
      new THREE.Vector3(-11, 6.0, -6), new THREE.Vector3(11, 6.0, -6),
      new THREE.Vector3(11, 6.0, 6), new THREE.Vector3(-11, 6.0, 6)
    ];
    telasGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts), cableMat));

    // Rede Central Oficial
    const netGameMat = new THREE.MeshBasicMaterial({{ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.75 }});
    const net = new THREE.Mesh(new THREE.PlaneGeometry(8.5, 1.0), netGameMat);
    net.position.set(0, 2.2, 0);
    net.rotation.y = Math.PI / 2;
    quadraGroup.add(net);

    // D) CHALÉS 1 A 5 (22 m² cada - Chalés 4 e 5 girados para a Casa do Sítio)
    const chalesGroups = [];
    const chaleWallMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const chaleRoofMat = new THREE.MeshStandardMaterial({{ color: 0x9a3412, roughness: 0.7 }});
    const chaleGlassMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.2, metalness: 0.8 }});
    const chalePilarMat = new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.9 }});
    const chaleDeckMat = new THREE.MeshStandardMaterial({{ color: 0x5c2d16, roughness: 0.75 }});

    chalesData.forEach(c => {{
      const cGroup = new THREE.Group();
      cGroup.position.set(c.lx, c.base_y, c.lz);
      if (c.id === 4 || c.id === 5) {{
        // Chalés 4 e 5 isolados girados frontalmente na direção da Casa do Sítio
        cGroup.rotation.y = Math.atan2(casaData.lx - c.lx, casaData.lz - c.lz);
      }} else {{
        cGroup.rotation.y = -salaoData.rot_rad;
      }}

      // Pilotis ancorados no relevo
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

      // Laje / Deck (5,50m x 4,00m)
      const baseDeck = new THREE.Mesh(new THREE.BoxGeometry(5.50, 0.20, 4.00), chaleDeckMat);
      baseDeck.position.set(0, 0.10, 0);
      cGroup.add(baseDeck);

      // Corpo principal (5,40m x 2,80m)
      const body = new THREE.Mesh(new THREE.BoxGeometry(5.40, 2.70, 2.80), chaleWallMat);
      body.position.set(0, 1.55, -0.55);
      cGroup.add(body);

      // Telhado duas águas
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

      // Varanda frontal
      const railMat = new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.5 }});
      const railFront = new THREE.Mesh(new THREE.BoxGeometry(5.40, 0.90, 0.06), railMat);
      railFront.position.set(0, 0.65, 1.95);
      const railL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railL.position.set(-2.67, 0.65, 1.35);
      const railR = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railR.position.set(2.67, 0.65, 1.35);
      cGroup.add(railFront, railL, railR);

      // Vidro panorâmico frontal
      const win = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.8), chaleGlassMat);
      win.position.set(0, 1.45, 0.86);
      cGroup.add(win);

      edifGroup.add(cGroup);
      chalesGroups.push({{ group: cGroup, base_y: c.base_y }});
    }});

    // =========================================================================
    // 6. INTERAÇÃO E NAVEGAÇÃO 3D
    // =========================================================================
    let currentZScale = 1.0;

    window.setZScale = function(val) {{
      currentZScale = parseFloat(val);
      document.getElementById('lblZScale').innerText = currentZScale.toFixed(2) + 'x' + (Math.abs(currentZScale - 1.0) < 0.01 ? ' (Real 1:1)' : '');
      const p = geom.attributes.position;
      for (let i = 0; i < p.count; i++) {{
        p.setY(i, baseElevations[i] * currentZScale);
      }}
      p.needsUpdate = true;
      geom.computeVertexNormals();

      casaGroup.position.y = casaData.base_y * currentZScale;
      salaoGroup.position.y = salaoData.base_y * currentZScale;
      quadraGroup.position.y = quadraData.base_y * currentZScale;
      chalesGroups.forEach(cg => {{
        cg.group.position.y = cg.base_y * currentZScale;
      }});
    }};

    window.setZScalePreset = function(val) {{
      document.getElementById('sliderZScale').value = val;
      setZScale(val);
    }};

    window.setSalaoOption = function(opt) {{
      optGroup1.visible = (opt === 1);
      optGroup2.visible = (opt === 2);
      optGroup3.visible = (opt === 3);
      for (let i = 1; i <= 3; i++) {{
        const b = document.getElementById('btnOpt' + i);
        if (b) b.classList.toggle('active', i === opt);
      }}
    }};

    window.goToView = function(view) {{
      let tCam, tTarget;
      if (view === 'casa') {{
        tCam = new THREE.Vector3(casaData.lx + 32, casaData.base_y + 18, casaData.lz + 36);
        tTarget = new THREE.Vector3(casaData.lx, casaData.base_y + 2.5, casaData.lz);
      }} else if (view === 'salao') {{
        tCam = new THREE.Vector3(salaoData.lx + 26, salaoData.base_y + 12, salaoData.lz + 22);
        tTarget = new THREE.Vector3(salaoData.lx, salaoData.base_y + 2.5, salaoData.lz);
      }} else if (view === 'quadra') {{
        tCam = new THREE.Vector3(quadraData.lx + 28, quadraData.base_y + 16, quadraData.lz + 24);
        tTarget = new THREE.Vector3(quadraData.lx, quadraData.base_y + 2.0, quadraData.lz);
      }} else if (view === 'chales') {{
        tCam = new THREE.Vector3(salaoData.lx + 45, salaoData.base_y + 30, salaoData.lz - 50);
        tTarget = new THREE.Vector3(salaoData.lx + 5, salaoData.base_y + 5.0, salaoData.lz - 25);
      }} else if (view === 'p1') {{
        tCam = new THREE.Vector3(-120, casaData.base_y + 90, -180);
        tTarget = new THREE.Vector3(-180, casaData.base_y + 20, -130);
      }} else if (view === 'p2') {{
        tCam = new THREE.Vector3(140, casaData.base_y + 90, -220);
        tTarget = new THREE.Vector3(80, casaData.base_y + 20, -160);
      }} else if (view === 'p3') {{
        tCam = new THREE.Vector3(260, casaData.base_y + 110, 60);
        tTarget = new THREE.Vector3(200, casaData.base_y + 25, 20);
      }} else if (view === 'panoramica') {{
        tCam = new THREE.Vector3(50, casaData.base_y + 420, 520);
        tTarget = new THREE.Vector3(0, casaData.base_y + 20, 0);
      }}

      if (tCam && tTarget) {{
        animateCamera(tCam, tTarget, 1000);
      }}
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

    window.toggleBoundary = function(show) {{ boundaryGroup.visible = show; }};
    window.toggleSectors = function(show) {{ sectorsGroup.visible = show; }};
    window.toggleSolar = function(show) {{ solarGroup.visible = show; }};
    window.toggleEdif = function(show) {{ edifGroup.visible = show; }};
    window.toggleTelas = function(show) {{ telasGroup.visible = show; }};
    window.toggleWire = function(show) {{ wireMesh.visible = show; }};

    window.addEventListener('resize', onWindowResize, false);
    function onWindowResize() {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }}

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}
    animate();
  </script>
</body>
</html>
"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_code)
    size_mb = os.path.getsize(HTML_OUT) / (1024 * 1024)
    print(f"6. Sucesso! Visualizador Geral salvo: {HTML_OUT} ({size_mb:.2f} MB)")

    # Copiar para index.html
    shutil.copyfile(HTML_OUT, INDEX_OUT)
    print(f"7. Arquivo {INDEX_OUT} atualizado com sucesso como página padrão!")
    print("================================================================================")

if __name__ == "__main__":
    main()
