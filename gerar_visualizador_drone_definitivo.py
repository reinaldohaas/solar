#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o Visualizador 3D Definitivo com:
1. Resolução TOTAL do MDT 1,0 m do SIGSC (1.377.194 vértices)
2. Ortofoto de Drone HD calibrada naturalmente (sem brilho plástico ou estouro)
3. Linha de Divisão e Perímetro do Sítio (18,60 ha) modelada em 3D Tube SOBRE O TERRENO
4. Linhas de Divisão dos Setores Solares (P1, P2, P3) modeladas em 3D SOBRE O TERRENO
5. Controles interativos no painel HUD
"""

import os
import io
import json
import base64
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
import numpy as np
from PIL import Image
import geopandas as gpd

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"

DRONE_LOCAL_TIF = os.path.join(SOLAR_DIR, "Ortofoto_Drone_Local.tif")
MDT_EXATO_TIF = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Exata.tif")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")

def main():
    print("1. Lendo Ortofoto de Drone com Calibração Fotográfica Natural...")
    with rasterio.open(DRONE_LOCAL_TIF) as src_drone:
        db = src_drone.bounds
        drone_w = src_drone.width
        drone_h = src_drone.height

        left = float(db.left)
        bottom = float(db.bottom)
        right = float(db.right)
        top = float(db.top)
        width_m = right - left
        depth_m = top - bottom
        cx = (left + right) / 2.0
        cy = (bottom + top) / 2.0

        # Resolução nítida de 3500 px
        tex_w = 3500
        tex_h = int(round(tex_w * drone_h / drone_w))
        print(f"   Dimensões métricas: {width_m:.2f} m x {depth_m:.2f} m")
        print(f"   Reamostrando textura para {tex_w}x{tex_h} px com filtro Lanczos...")
        rgba = src_drone.read(
            out_shape=(src_drone.count, tex_h, tex_w),
            resampling=Resampling.lanczos
        )

    rgb = np.transpose(rgba[:3], (1, 2, 0))
    if rgba.shape[0] == 4:
        alpha = rgba[3]
        mask = (alpha < 30)
        rgb[mask] = [38, 48, 33] # Verde escuro de mata para bordas fora do voo

    img_drone = Image.fromarray(rgb)
    buf = io.BytesIO()
    img_drone.save(buf, format='JPEG', quality=86)
    b64_drone = base64.b64encode(buf.getvalue()).decode('utf-8')
    print(f"   Ortofoto do Drone codificada em Base64 ({len(b64_drone)/(1024*1024):.2f} MB)")

    # 2. MDT SIGSC em resolução total de 1,0 metro (sem step=5)
    print("2. Lendo MDT do SIGSC em Resolução Nativa de 1,0 m...")
    with rasterio.open(MDT_EXATO_TIF) as src_mdt:
        elev = src_mdt.read(1)
        rows, cols = elev.shape

    z_min = float(np.nanmin(elev))
    z_max = float(np.nanmax(elev))
    z_range = z_max - z_min
    print(f"   Grade 3D Nativa: {cols} x {rows} = {rows*cols:,} vértices (1 vértice por metro!)")
    print(f"   Cotas: Min = {z_min:.2f} m | Max = {z_max:.2f} m | Desnível = {z_range:.2f} m")

    elev_clean = np.where(np.isnan(elev), z_min, elev)
    
    # Codificar em Uint16Array Base64 (precisão vertical milimétrica: 5 mm)
    uint16_arr = np.round(((elev_clean - z_min) / z_range) * 65535).astype(np.uint16)
    b64_heights = base64.b64encode(uint16_arr.tobytes()).decode('ascii')

    # Função para amostragem altimétrica 3D contínua ao longo de linhas
    res_x = width_m / cols
    res_y = depth_m / rows

    def sample_poly_3d(poly, step=1.2, dz=0.75):
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

    # 3. Linhas de Divisão e Limites do Sítio e Setores
    print("3. Densificando e projetando linhas de divisão 3D sobre o relevo...")
    gdf_sitio = gpd.read_file(GPKG_PATH, layer='limite_sitio')
    sitio_coords_3d = sample_poly_3d(gdf_sitio.geometry.iloc[0], step=1.2, dz=0.75)
    print(f"   Divisa do Sítio: {len(sitio_coords_3d)} vértices contínuos sobre o relevo")

    setores_coords = {}
    for s in ['p1', 'p2', 'p3']:
        gdf_s = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{s}')
        poly_s = gdf_s.union_all().convex_hull.buffer(3.5)
        setores_coords[s] = sample_poly_3d(poly_s, step=1.5, dz=0.55)
        print(f"   Divisão do Setor {s.upper()}: {len(setores_coords[s])} vértices")

    # 4. Vetores GPKG (Usinas P1, P2, P3, Salão e Quadra)
    print("4. Carregando estruturas de engenharia...")
    tables_data = []
    for setor in ['p1', 'p2', 'p3']:
        gdf = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor}')
        for _, r in gdf.iterrows():
            c = r.geometry.centroid
            tables_data.append({
                'setor': setor.upper(),
                'id': int(r['mesa_id']),
                'x': round(c.x - cx, 2),
                'y': round(r['cota_painel_inferior_m'] - z_min, 2),
                'z': round(-(c.y - cy), 2),
                'cota': float(r['cota_terreno_m'])
            })

    gdf_salao = gpd.read_file(GPKG_PATH, layer='edificacao_salao').iloc[0]
    sc = gdf_salao.geometry.centroid
    salao_data = {
        'x': round(sc.x - cx, 2),
        'y': round(gdf_salao['cota_piso_m'] - z_min, 2),
        'z': round(-(sc.y + 2.0 - cy), 2), # +2m Norte
        'cota': float(gdf_salao['cota_piso_m'])
    }

    gdf_campo = gpd.read_file(GPKG_PATH, layer='campo_de_areia').iloc[0]
    cc = gdf_campo.geometry.centroid
    campo_data = {
        'x': round(cc.x - cx, 2),
        'y': round(gdf_campo['cota_areia_m'] - z_min, 2),
        'z': round(-(cc.y + 2.0 - cy), 2), # +2m Norte
        'cota': float(gdf_campo['cota_areia_m'])
    }

    print("5. Montando HTML com motor WebGL de alta fidelidade...")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D — Sítio das Andorinhas (MDT LiDAR 1,0 m e Drone HD)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #0f172a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    #canvas-container {{ width: 100vw; height: 100vh; }}
    
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 380px;
      background: rgba(15, 23, 42, 0.94); color: #f8fafc; padding: 20px;
      border-radius: 12px; box-shadow: 0 12px 36px rgba(0,0,0,0.6);
      border: 1px solid rgba(255,255,255,0.14); backdrop-filter: blur(14px);
      z-index: 10; max-height: calc(100vh - 32px); overflow-y: auto;
    }}
    h1 {{ font-size: 16px; font-weight: 700; margin-bottom: 3px; color: #38bdf8; }}
    .badge {{ display: inline-block; font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 5px; background: #0369a1; color: #fff; margin-bottom: 12px; }}
    .badge-lidar {{ background: #059669; }}
    
    .stat-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    .stat-lbl {{ color: #94a3b8; }}
    .stat-val {{ font-weight: 600; color: #4ade80; }}
    .stat-highlight {{ color: #fbbf24; font-weight: 700; }}
    
    .slider-box {{ margin-top: 12px; background: rgba(30, 41, 59, 0.7); padding: 10px 12px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08); }}
    .slider-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 11.5px; color: #cbd5e1; }}
    .slider-val {{ font-weight: 700; color: #38bdf8; }}
    input[type=range] {{ width: 100%; accent-color: #38bdf8; cursor: pointer; }}
    
    .btn-group {{ margin-top: 12px; display: flex; flex-direction: column; gap: 6px; }}
    .btn {{
      background: #0284c7; border: none; color: white; padding: 8px 12px;
      border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
      transition: all 0.2s; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px;
    }}
    .btn:hover {{ background: #0369a1; transform: translateY(-1px); }}
    .btn-secondary {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; }}
    .btn-secondary:hover {{ background: #334155; }}
    .btn-accent {{ background: #059669; }}
    .btn-toggle-active {{ border-left: 4px solid #fbbf24; }}
    .btn-opt {{ font-size: 11px; padding: 7px 6px; text-align: center; border-radius: 6px; cursor: pointer; transition: all 0.2s; }}
    .btn-opt-active {{ background: #0284c7 !important; color: #ffffff !important; font-weight: 700 !important; border: 1px solid #38bdf8 !important; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }}

      position: absolute; bottom: 16px; left: 16px; background: rgba(15, 23, 42, 0.88);
      color: #94a3b8; padding: 8px 14px; border-radius: 8px; font-size: 11px;
      border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(8px);
    }}
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
    Construindo Relevo LiDAR 1,0 m e Ortofoto HD...
  </div>
  
  <div id="canvas-container"></div>
  
  <div id="panel">
    <h1>SÍTIO DAS ANDORINHAS 3D</h1>
    <div class="badge badge-lidar">MDT LiDAR 1,0 m Nativo ({rows*cols:,} vértices)</div>
    
    <div class="stat-row"><span class="stat-lbl">Resolução do Relevo:</span><span class="stat-val">1,0 metro (sem interpolação)</span></div>
    <div class="stat-row"><span class="stat-lbl">Cobertura do Drone:</span><span class="stat-val">{width_m:.0f} × {depth_m:.0f} m (137,8 ha)</span></div>
    <div class="stat-row"><span class="stat-lbl">Cota Mínima / Máxima:</span><span class="stat-val">{z_min:.1f} m / {z_max:.1f} m</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P1 (Otimizado):</span><span class="stat-val">114 mesas (925,7 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P2:</span><span class="stat-val">73 mesas (592,8 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P3:</span><span class="stat-val">46 mesas (373,5 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Salão com Telhado Reto:</span><span class="stat-val">18 módulos (10,4 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Campo de Areia e Redes 3D:</span><span class="stat-val">22 × 12 m (h=6 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">POTÊNCIA TOTAL USINA:</span><span class="stat-val stat-highlight">1.902,4 kWp (~1,90 MWp)</span></div>

    <!-- SIMULADOR SOLAR ANUAL & DIÁRIO -->
    <div class="slider-box" style="border: 1px solid rgba(251, 191, 36, 0.4); background: rgba(30, 41, 59, 0.85); margin-top: 10px;">
      <div style="font-weight: 700; color: #fbbf24; font-size: 12px; margin-bottom: 8px; display: flex; align-items: center; justify-content: space-between;">
        <span>☀️ SIMULADOR SOLAR (Lat: -27.40°)</span>
        <button id="btnPlaySun" onclick="toggleSunPlay()" style="background: #0284c7; border: none; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; font-weight: 600;">▶️ Simular Dia</button>
      </div>

      <!-- Seletor de Estação / Data (Simulador Anual) -->
      <div class="slider-row">
        <span>📅 Estação / Data:</span>
        <span id="valSeason" class="slider-val" style="color: #fde047;">21/Dez (Solstício Verão)</span>
      </div>
      <input type="range" id="sliderDayOfYear" min="1" max="365" step="1" value="355" oninput="onSolarInputChange()">
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 5px; margin-bottom: 10px;">
        <button class="btn btn-secondary" style="padding: 4px; font-size: 10px;" onclick="setSeasonPreset(355)">☀️ Solstício Verão</button>
        <button class="btn btn-secondary" style="padding: 4px; font-size: 10px;" onclick="setSeasonPreset(172)">❄️ Solstício Inverno</button>
        <button class="btn btn-secondary" style="padding: 4px; font-size: 10px;" onclick="setSeasonPreset(80)">🍂 Equinócio Outono</button>
        <button class="btn btn-secondary" style="padding: 4px; font-size: 10px;" onclick="setSeasonPreset(265)">🌸 Equinócio Primav.</button>
      </div>

      <!-- Seletor de Horário (Simulador Diário) -->
      <div class="slider-row">
        <span>⏰ Horário Solar:</span>
        <span id="valSolarHour" class="slider-val" style="font-size: 13px; color: #38bdf8;">12:00</span>
      </div>
      <input type="range" id="sliderSolarHour" min="5.5" max="18.5" step="0.05" value="12.0" oninput="onSolarInputChange()">

      <!-- Telemetria Solar em Tempo Real -->
      <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.08); font-size: 11px; color: #94a3b8;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>Altitude Solar:</span>
          <b id="valSolarAlt" style="color: #38bdf8;">86.0° (Zênite)</b>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 2px;">
          <span>Azimute Solar:</span>
          <b id="valSolarAz" style="color: #38bdf8;">0.0° (Norte)</b>
        </div>
        <div style="display: flex; justify-content: space-between;">
          <span>Projeção de Sombra:</span>
          <b id="valShadowLength" style="color: #4ade80;">Mínima (0,07x)</b>
        </div>
      </div>
    </div>

    <!-- Ajustes interativos de iluminação da cena -->
    <div class="slider-box">
      <div class="slider-row">
        <span>Brilho Geral / Exposição</span>
        <span id="valExposure" class="slider-val">1.00x</span>
      </div>
      <input type="range" id="sliderExposure" min="0.5" max="1.6" step="0.05" value="1.0" oninput="updateLighting()">

      <div class="slider-row" style="margin-top: 8px;">
        <span>Intensidade Luz Solar</span>
        <span id="valSun" class="slider-val">0.65</span>
      </div>
      <input type="range" id="sliderSun" min="0.0" max="1.2" step="0.05" value="0.65" oninput="updateLighting()">
    </div>

    <!-- Seletor de Opções Arquitetônicas: Salão 12x8m e Campo de Futebol de Areia -->
    <div class="slider-box" style="border: 1px solid rgba(56, 189, 248, 0.4); background: rgba(15, 23, 42, 0.92); margin-top: 10px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span style="font-weight: 700; color: #38bdf8; font-size: 11.5px;">🏛️ SALÃO 12×8m & CAMPO (SEM PAREDES)</span>
        <span id="badgeOpcao" style="font-size: 10px; font-weight: 700; background: #059669; color: white; padding: 2px 7px; border-radius: 4px;">OPÇÃO 1</span>
      </div>
      <div style="font-size: 11px; color: #94a3b8; margin-bottom: 8px; line-height: 1.35;">
        Salão 12x8m <b>100% aberto sem paredes</b>, alinhado à quadra de areia e deslocado +2m Norte.
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 8px;">
        <button class="btn btn-secondary btn-opt btn-opt-active" id="btnOpt1" onclick="setComplexOption(1)">🪵 1. Madeira Bruta</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt2" onclick="setComplexOption(2)">🏗️ 2. Metal 2 Águas</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt3" onclick="setComplexOption(3)">📐 3. 1 Água (Terreno)</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt4" onclick="setComplexOption(4)">💡 4. Arena Noturna</button>
      </div>

      <div id="descOpcao" style="font-size: 11px; background: rgba(0,0,0,0.35); padding: 8px 10px; border-radius: 6px; color: #e2e8f0; line-height: 1.4; border-left: 3px solid #38bdf8; min-height: 48px;">
        <b>Opção 1: Madeira Bruta / Rústica (Duas Águas)</b><br>
        Pilares de tora de eucalipto tratado (Ø26cm), tesouras de madeira rústica e telhas cerâmicas terracota. 100% aberto sem paredes.
      </div>

      <button class="btn btn-accent" onclick="focusOnComplex()" style="width: 100%; margin-top: 6px; font-size: 11.5px; padding: 7px 10px;">
        🎯 Focar Salão 12×8m & Campo (Close-up 3D)
      </button>
      <a href="visualizador_campo_salao.html" target="_blank" class="btn btn-secondary" style="width: 100%; margin-top: 5px; font-size: 11px; text-decoration: none; display: flex; align-items: center; justify-content: center; background: #0f766e; border-color: #14b8a6; color: white;">
        🚀 Abrir Visualizador Dedicado (Salão & Campo 3D)
      </a>
      <a href="galeria_fotos_drone.html" target="_blank" class="btn btn-secondary" style="width: 100%; margin-top: 5px; font-size: 11px; text-decoration: none; display: flex; align-items: center; justify-content: center; background: #15803d; border-color: #22c55e; color: white;">
        📸 Abrir Galeria (315 Fotos Aéreas em Cima da Obra)
      </a>
    </div>

    <div class="btn-group">
      <button class="btn btn-secondary btn-toggle-active" id="btnSolar" onclick="toggleSolarPanels()" style="background: #1e3a8a; border-color: #3b82f6;">☀️ Ocultar Painéis Solares</button>
      <button class="btn btn-secondary btn-toggle-active" id="btnBoundary" onclick="toggleBoundary()">🟡 Divisa do Sítio (18,60 ha) SOBRE o Terreno</button>
      <button class="btn btn-secondary btn-toggle-active" id="btnSectors" onclick="toggleSectors()">🔷 Divisões dos Setores Solares (P1, P2, P3)</button>
      <button class="btn btn-secondary" onclick="focusOn('p1')">🔎 Focar no Setor P1 (114 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p2')">🔎 Focar no Setor P2 (73 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3 (46 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Geral</button>
      <button class="btn btn-accent" onclick="toggleWireframe()">⚡ Alternar Malha LiDAR 1,0 m (Wireframe)</button>
    </div>
  </div>

  <div id="instructions">
    🖱️ <b>Mouse:</b> Botão esquerdo para girar | Botão direito para transladar | Roda para zoom
  </div>

  <script>
    const widthM = {width_m:.2f};
    const depthM = {depth_m:.2f};
    const rows = {rows};
    const cols = {cols};
    const zMin = {z_min:.2f};
    const zRange = {z_range:.2f};

    const tables = {json.dumps(tables_data)};
    const salao = {json.dumps(salao_data)};
    const campo = {json.dumps(campo_data)};
    const sitioCoords = {json.dumps(sitio_coords_3d)};
    const setoresCoords = {json.dumps(setores_coords)};

    const texDroneBase64 = "data:image/jpeg;base64,{b64_drone}";
    const heightsBase64 = "{b64_heights}";

    // Setup Three.js
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xdce7ef);
    scene.fog = new THREE.FogExp2(0xdce7ef, 0.00025);

    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 2, 12000);
    camera.position.set(-180, 600, 700);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: 'high-performance' }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputEncoding = THREE.sRGBEncoding;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.0;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.target.set(0, 45, 0);

    // Iluminação calibrada (equilibrada para não estourar a fotografia aérea)
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x475569, 0.60);
    hemiLight.position.set(0, 1000, 0);
    scene.add(hemiLight);

    const sun = new THREE.DirectionalLight(0xfffaed, 0.45);
    sun.position.set(-450, 950, -350);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.left = -800;
    sun.shadow.camera.right = 800;
    sun.shadow.camera.top = 800;
    sun.shadow.camera.bottom = -800;
    scene.add(sun);

    function updateLighting() {{
      const exp = parseFloat(document.getElementById('sliderExposure').value);
      const sunInt = parseFloat(document.getElementById('sliderSun').value);
      renderer.toneMappingExposure = exp;
      sun.intensity = sunInt;
      hemiLight.intensity = Math.max(0.2, 1.0 - sunInt * 0.5);
      document.getElementById('valExposure').innerText = exp.toFixed(2) + 'x';
      document.getElementById('valSun').innerText = sunInt.toFixed(2);
    }}

    // 1. Decodificação Binária do MDT LiDAR 1,0 m
    console.time('Decodificando Alturas LiDAR 1,0m');
    const binStr = atob(heightsBase64);
    const binLen = binStr.length;
    const bytes = new Uint8Array(binLen);
    for (let i = 0; i < binLen; i++) {{
      bytes[i] = binStr.charCodeAt(i);
    }}
    const heightsU16 = new Uint16Array(bytes.buffer);
    console.timeEnd('Decodificando Alturas LiDAR 1,0m');

    // 2. Construção da Malha de Alta Resolução (1 vértice por metro)
    console.time('Construindo BufferGeometry 1,0m');
    const numVertices = rows * cols;
    const positions = new Float32Array(numVertices * 3);
    const uvs = new Float32Array(numVertices * 2);
    const normals = new Float32Array(numVertices * 3);

    const dx = widthM / (cols - 1);
    const dz = depthM / (rows - 1);
    const x0 = -widthM / 2.0;
    const z0 = -depthM / 2.0;

    for (let r = 0; r < rows; r++) {{
      const z = z0 + r * dz;
      const v = 1.0 - (r / (rows - 1));
      for (let c = 0; c < cols; c++) {{
        const idx = r * cols + c;
        const h = (heightsU16[idx] / 65535.0) * zRange;
        positions[idx * 3] = x0 + c * dx;
        positions[idx * 3 + 1] = h;
        positions[idx * 3 + 2] = z;
        uvs[idx * 2] = c / (cols - 1);
        uvs[idx * 2 + 1] = v;
      }}
    }}

    // Normais analíticas precisas
    for (let r = 0; r < rows; r++) {{
      const rPrev = Math.max(0, r - 1);
      const rNext = Math.min(rows - 1, r + 1);
      const dZ = (rNext - rPrev) * dz;
      for (let c = 0; c < cols; c++) {{
        const cPrev = Math.max(0, c - 1);
        const cNext = Math.min(cols - 1, c + 1);
        const dX = (cNext - cPrev) * dx;
        const idx = r * cols + c;
        const hL = positions[(r * cols + cPrev) * 3 + 1];
        const hR = positions[(r * cols + cNext) * 3 + 1];
        const hU = positions[(rPrev * cols + c) * 3 + 1];
        const hD = positions[(rNext * cols + c) * 3 + 1];
        const slopeX = (hR - hL) / dX;
        const slopeZ = (hD - hU) / dZ;
        const len = Math.hypot(-slopeX, 1.0, -slopeZ);
        normals[idx * 3] = -slopeX / len;
        normals[idx * 3 + 1] = 1.0 / len;
        normals[idx * 3 + 2] = -slopeZ / len;
      }}
    }}

    const numQuads = (rows - 1) * (cols - 1);
    const indices = new Uint32Array(numQuads * 6);
    let k = 0;
    for (let r = 0; r < rows - 1; r++) {{
      for (let c = 0; c < cols - 1; c++) {{
        const i0 = r * cols + c;
        const i1 = i0 + 1;
        const i2 = i0 + cols;
        const i3 = i2 + 1;
        indices[k++] = i0;
        indices[k++] = i2;
        indices[k++] = i1;
        indices[k++] = i1;
        indices[k++] = i2;
        indices[k++] = i3;
      }}
    }}

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geom.setAttribute('normal', new THREE.BufferAttribute(normals, 3));
    geom.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
    geom.setIndex(new THREE.BufferAttribute(indices, 1));
    console.timeEnd('Construindo BufferGeometry 1,0m');

    // Material fosco natural (rugosidade 1.0, sem brilho plástico especular)
    const matTerrain = new THREE.MeshStandardMaterial({{
      color: 0xffffff,
      roughness: 1.0,
      metalness: 0.0,
      side: THREE.DoubleSide
    }});
    const terrain = new THREE.Mesh(geom, matTerrain);
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 3. Carregamento da Textura HD do Drone
    const texLoader = new THREE.TextureLoader();
    texLoader.load(
      texDroneBase64,
      function(texture) {{
        texture.encoding = THREE.sRGBEncoding;
        if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
          texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
        }}
        texture.generateMipmaps = true;
        texture.minFilter = THREE.LinearMipmapLinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.needsUpdate = true;
        matTerrain.map = texture;
        matTerrain.needsUpdate = true;
        const loadEl = document.getElementById('loading');
        if (loadEl) loadEl.style.display = 'none';
        renderer.render(scene, camera);
      }},
      undefined,
      function(err) {{
        console.error('Erro na textura:', err);
      }}
    );

    // 4. LINHA DE DIVISÃO DO SÍTIO MODELADA EM 3D SOBRE O TERRENO (18,60 ha)
    const boundaryGroup = new THREE.Group();
    const boundaryPts = sitioCoords.map(p => new THREE.Vector3(p[0], p[1], p[2]));
    
    // Curva contínua que abraça cada ondulação do relevo
    const boundaryCurve = new THREE.CatmullRomCurve3(boundaryPts, true);
    // Tubo 3D cilíndrico de 70 cm de espessura (diâmetro 0,70m)
    const boundaryTubeGeom = new THREE.TubeGeometry(boundaryCurve, Math.min(boundaryPts.length, 1600), 0.35, 6, true);
    const boundaryTubeMat = new THREE.MeshStandardMaterial({{
      color: 0xffea00,
      emissive: 0xffaa00,
      emissiveIntensity: 0.45,
      roughness: 0.3,
      metalness: 0.1
    }});
    const boundaryTubeMesh = new THREE.Mesh(boundaryTubeGeom, boundaryTubeMat);
    boundaryTubeMesh.castShadow = true;
    boundaryGroup.add(boundaryTubeMesh);

    // Linha de apoio de alta precisão
    const boundaryLineGeom = new THREE.BufferGeometry().setFromPoints(boundaryPts);
    const boundaryLineMat = new THREE.LineBasicMaterial({{ color: 0xffea00 }});
    const boundaryLine = new THREE.Line(boundaryLineGeom, boundaryLineMat);
    boundaryGroup.add(boundaryLine);
    scene.add(boundaryGroup);

    // 5. DIVISÕES DOS SETORES FOTOVOLTAICOS (P1, P2, P3) SOBRE O TERRENO
    const sectorsGroup = new THREE.Group();
    const sectorColors = {{
      p1: {{ color: 0x0284c7, emissive: 0x0369a1 }}, // Azul Ciano
      p2: {{ color: 0x10b981, emissive: 0x059669 }}, // Verde Esmeralda
      p3: {{ color: 0xf59e0b, emissive: 0xd97706 }}  // Âmbar / Laranja
    }};

    for (const [sKey, sPtsArr] of Object.entries(setoresCoords)) {{
      const sPoints = sPtsArr.map(p => new THREE.Vector3(p[0], p[1], p[2]));
      const sCurve = new THREE.CatmullRomCurve3(sPoints, true);
      const sTubeGeom = new THREE.TubeGeometry(sCurve, sPoints.length, 0.22, 5, true);
      const sMat = new THREE.MeshStandardMaterial({{
        color: sectorColors[sKey].color,
        emissive: sectorColors[sKey].emissive,
        emissiveIntensity: 0.4,
        roughness: 0.4
      }});
      const sMesh = new THREE.Mesh(sTubeGeom, sMat);
      sectorsGroup.add(sMesh);
    }}
    scene.add(sectorsGroup);

    // 6. Mesas Solares Solo (P1 114 mesas, P2 73 mesas, P3 46 mesas - Inclinadas 20° para o Norte)
    const solarGroup = new THREE.Group();
    const tableGeom = new THREE.BoxGeometry(8.0, 0.22, 4.32);
    // Rotação negativa em X inclina a face para o Norte (-Z) em direção ao Sol
    tableGeom.rotateX(-THREE.MathUtils.degToRad(20));

    const moduleMat = new THREE.MeshStandardMaterial({{ color: 0x1e3a8a, metalness: 0.8, roughness: 0.2 }});
    const postMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.6, roughness: 0.4 }});
    const postGeomFront = new THREE.CylinderGeometry(0.08, 0.08, 1.2, 6);
    const postGeomBack = new THREE.CylinderGeometry(0.08, 0.08, 2.3, 6);

    tables.forEach(t => {{
      const mesaMesh = new THREE.Mesh(tableGeom, moduleMat);
      mesaMesh.position.set(t.x, t.y + 0.95, t.z);
      mesaMesh.castShadow = true;
      solarGroup.add(mesaMesh);

      // Pés dianteiros (Norte, -Z, bordo inferior a ~0.60m)
      const postFront = new THREE.Mesh(postGeomFront, postMat);
      postFront.position.set(t.x - 2.5, t.y + 0.35, t.z - 1.4);
      solarGroup.add(postFront);

      // Pés traseiros (Sul, +Z, bordo elevado a ~2.15m)
      const postBack = new THREE.Mesh(postGeomBack, postMat);
      postBack.position.set(t.x + 2.5, t.y + 0.90, t.z + 1.4);
      solarGroup.add(postBack);
    }});
    scene.add(solarGroup);

    // 7. COMPLEXO INTEGRADO: SALÃO 12×8m (96 m²) & CAMPO DE FUTEBOL DE AREIA (22×12m)
    const complexGroup = new THREE.Group();
    scene.add(complexGroup);

    // Materiais compartilhados
    const matWallWhite = new THREE.MeshStandardMaterial({{ color: 0xf8fafc, roughness: 0.75 }});
    const matFloorConcrete = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.6 }});
    const matDarkFrame = new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.4, metalness: 0.6 }});
    const matGlass = new THREE.MeshPhysicalMaterial({{ color: 0x93c5fd, transparent: true, opacity: 0.35, roughness: 0.1, metalness: 0.1, transmission: 0.6 }});
    const matTeakWood = new THREE.MeshStandardMaterial({{ color: 0x9a6b43, roughness: 0.6 }});
    const matDarkWood = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.7 }});
    const matRoofTile = new THREE.MeshStandardMaterial({{ color: 0xc2410c, roughness: 0.75 }});

    // A) SALÃO 12x8m (100% ABERTO / SEM PAREDES - ALINHADO NO AZIMUTE 118° COM O CAMPO)
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salao.x, salao.y, salao.z);
    // Rigorosamente alinhado com a quadra de areia: Azimute 118° (Yaw = -28.02°)
    salaoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(salaoGroup);

    // Piso em cimento usinado polido (12,0m x 8,0m x 0,25m)
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.0, 0.25, 8.0), matFloorConcrete);
    salaoFloor.position.set(0, 0.125, 0);
    salaoFloor.receiveShadow = true;
    salaoGroup.add(salaoFloor);

    // PROLONGAMENTO DO CHÃO ATÉ O SOLO: Muro de embasamento contínuo descendo 2,5m
    const salaoPlinth = new THREE.Mesh(new THREE.BoxGeometry(12.0, 2.50, 8.0), matFloorConcrete);
    salaoPlinth.position.set(0, -1.13, 0);
    salaoPlinth.receiveShadow = true;
    salaoPlinth.castShadow = true;
    salaoGroup.add(salaoPlinth);

    // Escadaria frontal ampla de acesso à quadra de areia (3 degraus largos)
    const matStair = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.7 }});
    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), matStair);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      step.receiveShadow = true;
      salaoGroup.add(step);
    }}

    // ESTRUTURA 100% SEM PAREDES - Apenas os 6 pilares de sustentação perimetrais
    // Pilares base neutros
    const pilarBaseGeom = new THREE.BoxGeometry(0.25, 3.50, 0.25);
    const pilarBaseMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.5, roughness: 0.4 }});
    const pilarBaseGroup = new THREE.Group();
    [
      [-5.8, 1.75, -3.8], [0, 1.75, -3.8], [5.8, 1.75, -3.8],
      [-5.8, 1.75, 3.8],  [0, 1.75, 3.8],  [5.8, 1.75, 3.8]
    ].forEach(pos => {{
      const p = new THREE.Mesh(pilarBaseGeom, pilarBaseMat);
      p.position.set(pos[0], pos[1], pos[2]);
      p.castShadow = true;
      pilarBaseGroup.add(p);
    }});
    salaoGroup.add(pilarBaseGroup);

    // Usina Solar de Cobertura (18 Módulos de 580W TOPCon = 10,44 kWp)
    // Função para criar fileiras de módulos solares alinhadas rigorosamente ao salão
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

    // B) CAMPO DE FUTEBOL DE AREIA (22m x 12m)
    const campoGroup = new THREE.Group();
    campoGroup.position.set(campo.x, campo.y, campo.z);
    campoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(campoGroup);

    const sandMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 0.25, 12.0),
      new THREE.MeshStandardMaterial({{ color: 0xfcd34d, roughness: 0.95 }})
    );
    sandMesh.position.set(0, 0.125, 0);
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    const sandBorder = new THREE.Mesh(
      new THREE.BoxGeometry(22.4, 0.35, 12.4),
      matDarkWood
    );
    sandBorder.position.set(0, 0.15, 0);
    sandBorder.receiveShadow = true;
    campoGroup.add(sandBorder);

    // Redes perimetrais de proteção de 6,0 m de altura
    const netPerimMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 6.0, 12.0),
      new THREE.MeshBasicMaterial({{ color: 0x334155, wireframe: true, transparent: true, opacity: 0.35 }})
    );
    netPerimMesh.position.set(0, 3.0, 0);
    campoGroup.add(netPerimMesh);

    const postGeomCorner = new THREE.CylinderGeometry(0.08, 0.08, 6.2, 8);
    const postMatSteel = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }});
    [[-11, -6], [11, -6], [11, 6], [-11, 6]].forEach(pt => {{
      const pc = new THREE.Mesh(postGeomCorner, postMatSteel);
      pc.position.set(pt[0], 3.1, pt[1]);
      campoGroup.add(pc);
    }});

    // Traves Oficiais de Futebol de Areia (3,00m x 2,20m)
    const goalMat = new THREE.MeshStandardMaterial({{ color: 0xfef08a, roughness: 0.4 }});
    function createBeachGoal(isLeft) {{
      const goalG = new THREE.Group();
      const goalX = isLeft ? -10.2 : 10.2;
      const postG = new THREE.CylinderGeometry(0.06, 0.06, 2.20, 8);
      const crossbarG = new THREE.CylinderGeometry(0.06, 0.06, 3.0, 8);
      crossbarG.rotateZ(Math.PI / 2);

      const p1 = new THREE.Mesh(postG, goalMat); p1.position.set(0, 1.10, -1.5); goalG.add(p1);
      const p2 = new THREE.Mesh(postG, goalMat); p2.position.set(0, 1.10, 1.5); goalG.add(p2);
      const cb = new THREE.Mesh(crossbarG, goalMat); cb.position.set(0, 2.20, 0); goalG.add(cb);

      const netBox = new THREE.Mesh(
        new THREE.BoxGeometry(0.9, 2.2, 3.0),
        new THREE.MeshBasicMaterial({{ color: 0xf8fafc, wireframe: true, transparent: true, opacity: 0.45 }})
      );
      netBox.position.set(isLeft ? -0.45 : 0.45, 1.10, 0);
      goalG.add(netBox);

      goalG.position.set(goalX, 0.25, 0);
      return goalG;
    }}
    campoGroup.add(createBeachGoal(true));
    campoGroup.add(createBeachGoal(false));

    // -------------------------------------------------------------------------
    // SUBGRUPO OPÇÃO 1: MADEIRA BRUTA / RÚSTICA (SEM PAREDES)
    // -------------------------------------------------------------------------
    const opt1Group = new THREE.Group();
    salaoGroup.add(opt1Group);

    const rusticWoodMat = new THREE.MeshStandardMaterial({{ color: 0x4a2e18, roughness: 0.85 }});
    const tileCeramicMat = new THREE.MeshStandardMaterial({{ color: 0xa0522d, roughness: 0.7 }});

    // 6 Pilares de Tora Rústica (Diâmetro 30cm, Altura 3.6m)
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

    // Vigas Mestres Longitudinais de Tora
    const viga1 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga1.rotation.z = Math.PI / 2; viga1.position.set(0, 3.65, -3.7);
    const viga2 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.2, 12), rusticWoodMat);
    viga2.rotation.z = Math.PI / 2; viga2.position.set(0, 3.65, 3.7);
    opt1Group.add(viga1, viga2);

    // Tesouras Rústicas de Tora
    [-5.7, 0, 5.7].forEach(x => {{
      const tieBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 8.0, 10), rusticWoodMat);
      tieBeam.rotation.x = Math.PI / 2; tieBeam.position.set(x, 3.7, 0);
      const postKing = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 1.6, 10), rusticWoodMat);
      postKing.position.set(x, 4.5, 0);
      opt1Group.add(tieBeam, postKing);
    }});

    // Telhado Duas Águas com Telha Colonial Terracota (Cumeeira no Centro Z = 0)
    const roofWoodN = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofWoodN.rotation.x = -THREE.MathUtils.degToRad(21.8);
    roofWoodN.position.set(0, 4.45, -2.18);
    roofWoodN.castShadow = true;
    const roofWoodS = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofWoodS.rotation.x = THREE.MathUtils.degToRad(21.8);
    roofWoodS.position.set(0, 4.45, 2.18);
    roofWoodS.castShadow = true;
    opt1Group.add(roofWoodN, roofWoodS);

    // Viga de Cumeeira Central e Capa de Cumeeira Cerâmica em Meia-Cana
    const ridgeBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 13.2, 12), rusticWoodMat);
    ridgeBeam.rotation.z = Math.PI / 2;
    ridgeBeam.position.set(0, 5.25, 0);
    const ridgeTileMat = new THREE.MeshStandardMaterial({{ color: 0x8a3818, roughness: 0.65 }});
    const ridgeCap = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 13.3, 16), ridgeTileMat);
    ridgeCap.rotation.z = Math.PI / 2;
    ridgeCap.position.set(0, 5.28, 0);
    ridgeCap.castShadow = true;
    opt1Group.add(ridgeBeam, ridgeCap);

    // 18 Painéis Solares na Cobertura Colonial (Opção 1)
    const solarGroupOpt1 = new THREE.Group();
    const r1Opt1 = createSalaoSolarRow(9, 1.134, 1.95);
    r1Opt1.rotation.x = -THREE.MathUtils.degToRad(21.8);
    r1Opt1.position.set(0, 4.88, -1.07);
    const r2Opt1 = createSalaoSolarRow(9, 1.134, 1.95);
    r2Opt1.rotation.x = -THREE.MathUtils.degToRad(21.8);
    r2Opt1.position.set(0, 4.10, -3.02);
    solarGroupOpt1.add(r1Opt1, r2Opt1);
    opt1Group.add(solarGroupOpt1);

    // -------------------------------------------------------------------------
    // SUBGRUPO OPÇÃO 2: ESTRUTURA METÁLICA DUAS ÁGUAS (SEM PAREDES)
    // -------------------------------------------------------------------------
    const opt2Group = new THREE.Group();
    opt2Group.visible = false;
    salaoGroup.add(opt2Group);

    const steelDarkMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }});
    const panelSandwichMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.5, roughness: 0.4 }});

    // 6 Pilares Tubulares Pretos
    pilarPositions.forEach(p => {{
      const pSteel = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3.6, 0.2), steelDarkMat);
      pSteel.position.set(p[0], 1.8, p[2]);
      pSteel.castShadow = true;
      opt2Group.add(pSteel);
    }});

    // Telhas Termoacústicas Grafite Duas Águas
    const roofSteelN = new THREE.Mesh(new THREE.BoxGeometry(12.6, 0.08, 4.6), panelSandwichMat);
    roofSteelN.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofSteelN.position.set(0, 4.3, -2.15);
    roofSteelN.castShadow = true;
    const roofSteelS = new THREE.Mesh(new THREE.BoxGeometry(12.6, 0.08, 4.6), panelSandwichMat);
    roofSteelS.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofSteelS.position.set(0, 4.3, 2.15);
    roofSteelS.castShadow = true;
    opt2Group.add(roofSteelN, roofSteelS);

    // 18 Painéis Solares na Cobertura Metálica (Opção 2)
    const solarGroupOpt2 = new THREE.Group();
    const r1Opt2 = createSalaoSolarRow(9, 1.134, 1.95);
    r1Opt2.rotation.x = -THREE.MathUtils.degToRad(18.0);
    r1Opt2.position.set(0, 4.74, -1.09);
    const r2Opt2 = createSalaoSolarRow(9, 1.134, 1.95);
    r2Opt2.rotation.x = -THREE.MathUtils.degToRad(18.0);
    r2Opt2.position.set(0, 4.10, -3.09);
    solarGroupOpt2.add(r1Opt2, r2Opt2);
    opt2Group.add(solarGroupOpt2);

    // -------------------------------------------------------------------------
    // SUBGRUPO OPÇÃO 3: TELHADO 1 ÁGUA INCLINADO COMO O TERRENO (~9,3° DECLIVE)
    // -------------------------------------------------------------------------
    const opt3Group = new THREE.Group();
    opt3Group.visible = false;
    salaoGroup.add(opt3Group);

    const opt3CeilingWood = new THREE.MeshStandardMaterial({{ color: 0x92400e, roughness: 0.6 }});

    // Pilares Traseiros mais altos (4.3m)
    [-5.7, 0, 5.7].forEach(x => {{
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.3, 0.2), steelDarkMat);
      pBack.position.set(x, 2.15, -3.7);
      pBack.castShadow = true;
      opt3Group.add(pBack);
    }});
    // Pilares Frontais voltados para a quadra mais baixos (3.0m)
    [-5.7, 0, 5.7].forEach(x => {{
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3.0, 0.2), steelDarkMat);
      pFront.position.set(x, 1.5, 3.7);
      pFront.castShadow = true;
      opt3Group.add(pFront);
    }});

    // Cobertura Mono-Inclinada (Caimento de 9.3° descendo em direção à quadra de areia)
    const roofMonoGroup = new THREE.Group();
    roofMonoGroup.position.set(0, 3.65, 0);
    roofMonoGroup.rotation.x = THREE.MathUtils.degToRad(9.3);

    const roofMonoSlab = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.12, 9.2), panelSandwichMat);
    roofMonoSlab.castShadow = true;
    const roofMonoCeil = new THREE.Mesh(new THREE.BoxGeometry(12.7, 0.02, 9.1), opt3CeilingWood);
    roofMonoCeil.position.set(0, -0.07, 0);
    roofMonoGroup.add(roofMonoSlab, roofMonoCeil);
    opt3Group.add(roofMonoGroup);

    // 18 Painéis Solares no Telhado 1 Água (Opção 3)
    const solarGroupOpt3 = new THREE.Group();
    const r1Opt3 = createSalaoSolarRow(9, 1.134, 1.95);
    r1Opt3.position.set(0, 0.08, -2.15);
    const r2Opt3 = createSalaoSolarRow(9, 1.134, 1.95);
    r2Opt3.position.set(0, 0.08, 2.15);
    solarGroupOpt3.add(r1Opt3, r2Opt3);
    roofMonoGroup.add(solarGroupOpt3);

    // -------------------------------------------------------------------------
    // SUBGRUPO OPÇÃO 4: ARENA ESPORTIVA NOTURNA (4 TORRES DE REFLETORES LED)
    // -------------------------------------------------------------------------
    const opt4Group = new THREE.Group();
    opt4Group.visible = false;
    campoGroup.add(opt4Group);

    const towerGeom = new THREE.CylinderGeometry(0.09, 0.16, 7.5, 8);
    const matGalvanized = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.8, roughness: 0.3 }});
    const matFloodlight = new THREE.MeshStandardMaterial({{ color: 0x0f172a, roughness: 0.5 }});
    const matLedGlass = new THREE.MeshBasicMaterial({{ color: 0xffffff }});

    const floodLightsList = [];

    const towerCorners = [
      [-11.5, -6.5],
      [11.5, -6.5],
      [11.5, 6.5],
      [-11.5, 6.5]
    ];

    towerCorners.forEach((tc, idx) => {{
      const towG = new THREE.Group();
      const mast = new THREE.Mesh(towerGeom, matGalvanized);
      mast.position.set(0, 3.75, 0);
      mast.castShadow = true;
      towG.add(mast);

      const crossarm = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.08, 0.10), matGalvanized);
      crossarm.position.set(0, 7.45, 0);
      towG.add(crossarm);

      [-0.4, 0.4].forEach(off => {{
        const flBox = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.22, 0.18), matFloodlight);
        flBox.position.set(off, 7.40, 0);
        towG.add(flBox);

        const flGlass = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.18, 0.02), matLedGlass);
        flGlass.position.set(off, 7.39, 0.10);
        towG.add(flGlass);
      }});

      towG.position.set(tc[0], 0.15, tc[1]);
      opt4Group.add(towG);

      const spot = new THREE.SpotLight(0xfffaed, 0.0, 45, Math.PI / 3, 0.5, 1.2);
      spot.position.set(campo.x + tc[0], campo.y + 7.5, campo.z + tc[1]);
      spot.target.position.set(campo.x, campo.y + 0.2, campo.z);
      spot.target.updateMatrixWorld();
      scene.add(spot.target);
      scene.add(spot);
      floodLightsList.push(spot);
    }});

    const courtLinesGeom = new THREE.BufferGeometry();
    const clPts = [
      new THREE.Vector3(-10, 0.26, -5), new THREE.Vector3(10, 0.26, -5),
      new THREE.Vector3(10, 0.26, -5), new THREE.Vector3(10, 0.26, 5),
      new THREE.Vector3(10, 0.26, 5), new THREE.Vector3(-10, 0.26, 5),
      new THREE.Vector3(-10, 0.26, 5), new THREE.Vector3(-10, 0.26, -5),
      new THREE.Vector3(0, 0.26, -5), new THREE.Vector3(0, 0.26, 5)
    ];
    courtLinesGeom.setFromPoints(clPts);
    const courtLinesMat = new THREE.LineBasicMaterial({{ color: 0x0284c7, linewidth: 3 }});
    const courtLines = new THREE.LineSegments(courtLinesGeom, courtLinesMat);
    opt4Group.add(courtLines);

    const netVolleyGroup = new THREE.Group();
    const postVGeom = new THREE.CylinderGeometry(0.04, 0.04, 2.3, 8);
    const pv1 = new THREE.Mesh(postVGeom, matDarkFrame); pv1.position.set(0, 1.15, -5.5); netVolleyGroup.add(pv1);
    const pv2 = new THREE.Mesh(postVGeom, matDarkFrame); pv2.position.set(0, 1.15, 5.5); netVolleyGroup.add(pv2);
    const netMeshV = new THREE.Mesh(
      new THREE.BoxGeometry(0.04, 1.0, 11.0),
      new THREE.MeshBasicMaterial({{ color: 0xf8fafc, wireframe: true, transparent: true, opacity: 0.6 }})
    );
    netMeshV.position.set(0, 1.70, 0); netVolleyGroup.add(netMeshV);
    opt4Group.add(netVolleyGroup);

    [[-10, -5], [10, -5], [10, 5], [-10, 5]].forEach(cp => {{
      const cornerFlag = new THREE.Group();
      const cPost = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.5, 6), new THREE.MeshBasicMaterial({{ color: 0xfacc15 }}));
      cPost.position.set(0, 0.75, 0); cornerFlag.add(cPost);
      const cFlag = new THREE.Mesh(new THREE.BoxGeometry(0.01, 0.25, 0.35), new THREE.MeshBasicMaterial({{ color: 0xef4444 }}));
      cFlag.position.set(0, 1.35, 0.175); cornerFlag.add(cFlag);
      cornerFlag.position.set(cp[0], 0.25, cp[1]);
      opt4Group.add(cornerFlag);
    }});

    // 9. ESFERA SOLAR VISÍVEL NO CÉU
    const sunSphereGeom = new THREE.SphereGeometry(32, 16, 16);
    const sunSphereMat = new THREE.MeshBasicMaterial({{ color: 0xfff08a }});
    const sunSphere = new THREE.Mesh(sunSphereGeom, sunSphereMat);
    scene.add(sunSphere);

    // --- CÁLCULOS ASTRONÔMICOS DO SIMULADOR SOLAR ---
    // Coordenadas geográficas exatas do Sítio das Andorinhas
    const LAT_RAD = -27.395 * Math.PI / 180.0; // Latitude Sul
    const LON_DEG = -49.347;                    // Longitude Oeste
    const R_SUN_ORBIT = 1600;                   // Raio da órbita da luz solar 3D

    function computeSunAngles(dayOfYear, hourOfDay) {{
      // Declinação solar (radianos)
      const b = (360.0 / 365.0) * (dayOfYear - 81) * Math.PI / 180.0;
      const decl = 23.45 * Math.PI / 180.0 * Math.sin(b);

      // Equação do tempo (minutos)
      const eot = 9.87 * Math.sin(2 * b) - 7.53 * Math.cos(b) - 1.5 * Math.sin(b);
      // Correção de longitude para o fuso UTC-3 (Meridiano padrão -45°)
      const solarTime = hourOfDay + (4.0 * (LON_DEG - (-45.0)) + eot) / 60.0;

      // Ângulo horário (15° por hora a partir do meio-dia solar)
      const omega = (solarTime - 12.0) * 15.0 * Math.PI / 180.0;

      // Vetores direcionais analíticos (Leste, Norte, Zênite)
      const vEast = -Math.cos(decl) * Math.sin(omega);
      const vNorth = -Math.sin(LAT_RAD) * Math.cos(decl) * Math.cos(omega) + Math.cos(LAT_RAD) * Math.sin(decl);
      const vUp = Math.cos(LAT_RAD) * Math.cos(decl) * Math.cos(omega) + Math.sin(LAT_RAD) * Math.sin(decl);

      // Altitude solar
      const alpha = Math.asin(Math.max(-1.0, Math.min(1.0, vUp)));
      
      // Azimute solar a partir do Norte (0° N, 90° L, 180° S, 270° O)
      let azDeg = Math.atan2(vEast, vNorth) * 180.0 / Math.PI;
      if (azDeg < 0) azDeg += 360.0;

      return {{
        alphaRad: alpha,
        alphaDeg: alpha * 180.0 / Math.PI,
        gammaDeg: azDeg,
        vEast: vEast,
        vNorth: vNorth,
        vUp: vUp,
        declDeg: decl * 180.0 / Math.PI
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
        if (rem <= monthNames[m].days) {{
          return rem + ' de ' + monthNames[m].name;
        }}
        rem -= monthNames[m].days;
      }}
      return '31 de Dez';
    }}

    function getCardinalDirection(deg) {{
      const dirs = ['N', 'NNE', 'NE', 'ENE', 'L', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO', 'N'];
      const idx = Math.round(deg / 22.5);
      return dirs[idx];
    }}

    let isSunPlaying = false;
    function toggleSunPlay() {{
      isSunPlaying = !isSunPlaying;
      const btn = document.getElementById('btnPlaySun');
      btn.textContent = isSunPlaying ? '⏸️ Pausar' : '▶️ Simular Dia';
      btn.style.background = isSunPlaying ? '#e11d48' : '#0284c7';
    }}

    function setSeasonPreset(day) {{
      document.getElementById('sliderDayOfYear').value = day;
      onSolarInputChange();
    }}

    function onSolarInputChange() {{
      const day = parseInt(document.getElementById('sliderDayOfYear').value);
      const hour = parseFloat(document.getElementById('sliderSolarHour').value);
      updateSolarSimulation(day, hour);
    }}

    function updateSolarSimulation(day, hour) {{
      if (day === undefined) day = parseInt(document.getElementById('sliderDayOfYear').value);
      if (hour === undefined) hour = parseFloat(document.getElementById('sliderSolarHour').value);

      const res = computeSunAngles(day, hour);
      const alpha = res.alphaRad;
      const gamma = res.gammaRad;

      // Atualizar textos e indicadores do HUD
      let seasonDesc = dayOfYearToDateStr(day);
      if (day >= 350 || day <= 5) seasonDesc += ' (Solstício Verão)';
      else if (day >= 165 && day <= 178) seasonDesc += ' (Solstício Inverno)';
      else if (day >= 75 && day <= 85) seasonDesc += ' (Equinócio Outono)';
      else if (day >= 260 && day <= 270) seasonDesc += ' (Equinócio Primav.)';
      document.getElementById('valSeason').innerText = seasonDesc;

      const hInt = Math.floor(hour);
      const mInt = Math.floor((hour - hInt) * 60);
      document.getElementById('valSolarHour').innerText = (hInt < 10 ? '0' : '') + hInt + ':' + (mInt < 10 ? '0' : '') + mInt;

      document.getElementById('valSolarAlt').innerText = res.alphaDeg.toFixed(1) + '°' + (res.alphaDeg <= 0 ? ' (Noite)' : '');
      document.getElementById('valSolarAz').innerText = res.gammaDeg.toFixed(1) + '° (' + getCardinalDirection(res.gammaDeg) + ')';

      if (res.alphaDeg > 0) {{
        const shadowRatio = 1.0 / Math.tan(Math.max(0.08, alpha));
        document.getElementById('valShadowLength').innerText = shadowRatio.toFixed(2) + 'x h (' + (shadowRatio < 0.5 ? 'Muito Curta' : shadowRatio < 1.5 ? 'Média' : 'Longa') + ')';
      }} else {{
        document.getElementById('valShadowLength').innerText = 'Sem Sol Direto';
      }}

      // Reposicionar a Luz e a Esfera Solar no Espaço 3D
      // Tridimensionalidade: +X = Leste (vEast), -X = Oeste, +Y = Zênite (vUp), -Z = Norte (vNorth), +Z = Sul
      const sx = R_SUN_ORBIT * res.vEast;
      const sy = 45.0 + Math.max(-200.0, R_SUN_ORBIT * res.vUp);
      const sz = -R_SUN_ORBIT * res.vNorth;

      sun.position.set(sx, sy, sz);
      sun.target.position.set(0, 45, 0);
      sun.target.updateMatrixWorld();

      sunSphere.position.set(sx, sy, sz);

      if (res.alphaDeg > 0) {{
        sunSphere.visible = true;
        const curSunInt = parseFloat(document.getElementById('sliderSun').value) || 0.65;
        sun.intensity = Math.min(1.2, curSunInt * Math.max(0.3, Math.sin(alpha)));
        
        // Coloração do Sol e do Céu de acordo com a altitude solar
        if (res.alphaDeg < 15) {{
          sun.color.setHex(0xf97316); // Dourado crepuscular
          sunSphereMat.color.setHex(0xf97316);
          renderer.setClearColor(0x331b14, 1);
        }} else if (res.alphaDeg < 35) {{
          sun.color.setHex(0xfde047); // Dourado quente
          sunSphereMat.color.setHex(0xfde047);
          renderer.setClearColor(0x0f2942, 1);
        }} else {{
          sun.color.setHex(0xfffaed); // Branco pleno
          sunSphereMat.color.setHex(0xfff3b0);
          renderer.setClearColor(0x0f172a, 1);
        }}
        hemiLight.intensity = Math.max(0.25, 0.55 * Math.sin(alpha));
      }} else {{
        // Noite / Abaixo do Horizonte
        sunSphere.visible = false;
        sun.intensity = 0.0;
        hemiLight.intensity = 0.12;
        renderer.setClearColor(0x020617, 1);
      }}
    }}

    // --- FUNÇÕES DE INTERAÇÃO DO HUD ---
    let showSolarPanels = true;
    function toggleSolarPanels() {{
      showSolarPanels = !showSolarPanels;
      solarGroup.visible = showSolarPanels;
      solarGroupOpt1.visible = showSolarPanels;
      solarGroupOpt2.visible = showSolarPanels;
      solarGroupOpt3.visible = showSolarPanels;
      const btn = document.getElementById('btnSolar');
      btn.classList.toggle('btn-toggle-active', showSolarPanels);
      btn.textContent = showSolarPanels ? '☀️ Ocultar Painéis Solares' : '☀️ Exibir Painéis Solares';
      btn.style.background = showSolarPanels ? '#1e3a8a' : '#1e293b';
    }}

    // --- FUNÇÕES DE SELEÇÃO DE OPÇÕES ARQUITETÔNICAS (SALÃO 12x8m & CAMPO) ---
    let currentOption = 1;
    const optionDescriptions = {{
      1: "<b>Opção 1: Lounge Panorâmico & Deck com Pergolado</b><br>Deck em madeira nobre teca (12×4,5m) com pergolado ripado, ombrelones e mesas bistrô interligando o salão de 96 m² à quadra de areia.",
      2: "<b>Opção 2: Camarote & Varandão com Arquibancada</b><br>Varandão coberto amplo (12×3m) e arquibancada integrada em 2 níveis de madeira e concreto voltada para a lateral da quadra de areia para assistir aos jogos.",
      3: "<b>Opção 3: Pavilhão Rústico Colonial (Duas Águas)</b><br>Salão com telhado aparente em duas águas e tesouras de madeira rústica, cumeeira a 5,2m, beiral estendido de 1,2m, pilares de eucalipto e quiosque de apoio.",
      4: "<b>Opção 4: Arena Esportiva Noturna com Refletores</b><br>4 Torres de iluminação esportiva de 7,5m nos cantos da quadra com refletores LED de alta potência (luz ativa no 3D!), rede de futevôlei e demarcações oficiais."
    }};

    function setComplexOption(opt) {{
      currentOption = opt;
      opt1Group.visible = (opt === 1);
      opt2Group.visible = (opt === 2);
      opt3Group.visible = (opt === 3);
      opt4Group.visible = (opt === 4);

      pilarBaseGroup.visible = (opt !== 1);

      // Refletores de LED da Opção 4
      floodLightsList.forEach(light => {{
        light.intensity = (opt === 4) ? 1.4 : 0.0;
      }});

      // Atualizar botões HUD
      for (let i = 1; i <= 4; i++) {{
        const btn = document.getElementById('btnOpt' + i);
        if (btn) {{
          btn.classList.toggle('btn-opt-active', i === opt);
        }}
      }}

      document.getElementById('badgeOpcao').innerText = 'OPÇÃO ' + opt;
      document.getElementById('descOpcao').innerHTML = optionDescriptions[opt];
    }}

    function focusOnComplex() {{
      const midX = (salao.x + campo.x) / 2.0;
      const midY = (salao.y + campo.y) / 2.0;
      const midZ = (salao.z + campo.z) / 2.0;
      controls.target.set(midX, midY + 1.5, midZ);
      camera.position.set(midX - 26, midY + 16, midZ + 32);
    }}

    function focusOn(target) {{
      if (target === 'p1') {{
        const t0 = tables[0];
        controls.target.set(t0.x + 30, t0.y + 10, t0.z);
        camera.position.set(t0.x - 60, t0.y + 70, t0.z + 120);
      }} else if (target === 'p2') {{
        const p2Table = tables.find(t => t.setor === 'P2') || tables[0];
        controls.target.set(p2Table.x + 20, p2Table.y, p2Table.z);
        camera.position.set(p2Table.x - 70, p2Table.y + 70, p2Table.z + 100);
      }} else if (target === 'p3') {{
        const p3Table = tables.find(t => t.setor === 'P3') || tables[0];
        controls.target.set(p3Table.x, p3Table.y, p3Table.z);
        camera.position.set(p3Table.x - 50, p3Table.y + 50, p3Table.z + 80);
      }} else if (target === 'salao') {{
        focusOnComplex();
      }} else {{
        controls.target.set(0, 45, 0);
        camera.position.set(-180, 600, 700);
      }}
    }}

    let isWire = false;
    function toggleWireframe() {{
      isWire = !isWire;
      matTerrain.wireframe = isWire;
    }}

    let showBoundary = true;
    function toggleBoundary() {{
      showBoundary = !showBoundary;
      boundaryGroup.visible = showBoundary;
      document.getElementById('btnBoundary').classList.toggle('btn-toggle-active', showBoundary);
    }}

    let showSectors = true;
    function toggleSectors() {{
      showSectors = !showSectors;
      sectorsGroup.visible = showSectors;
      document.getElementById('btnSectors').classList.toggle('btn-toggle-active', showSectors);
    }}

    window.addEventListener('resize', () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    // Inicialização da Simulação Solar
    updateSolarSimulation(355, 12.0);

    function animate() {{
      requestAnimationFrame(animate);
      if (isSunPlaying) {{
        let h = parseFloat(document.getElementById('sliderSolarHour').value);
        h += 0.035; // Incremento suave de horário (~2 min por frame)
        if (h > 18.5) h = 5.5; // Loop do amanhecer ao pôr do sol
        document.getElementById('sliderSolarHour').value = h.toFixed(2);
        onSolarInputChange();
      }}
      controls.update();
      renderer.render(scene, camera);
    }}
    animate();
    animate();
  </script>
</body>
</html>"""

    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Visualizador 3D Atualizado com Sucesso: {HTML_OUT}")
    sz_mb = os.path.getsize(HTML_OUT) / (1024*1024)
    print(f"Tamanho do arquivo HTML: {sz_mb:.2f} MB")

if __name__ == '__main__':
    main()
