#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
GERADOR DO VISUALIZADOR 3D DEDICADO: CASA DO SÍTIO E ARREDORES (SIGSC NATIVO)
MDT LiDAR 1,0 m Oficial (SIGSC) & Ortofoto Oficial 39 cm (SIGSC)
===============================================================================
- Alinhamento rigoroso dos telhados da Casa do Sítio com telhado1.kmz e telhado2.kmz
- Terreno natural do MDT SIGSC sob a casa (sem elevação / sem montículo artificial)
- Salão de Festas anterior recuperado: estrutura aberta sem paredes, 10 pilares,
  tesouras de madeira rústica, opções arquitetônicas e usina solar de 10,44 kWp
- Quadra de Areia 22x12m e Chalés 1 a 5 georreferenciados
- Escala estrita 1:1 (1m horizontal = 1m vertical)
- EXCLUSIVAMENTE dados oficiais do SIGSC (sem dados de drones)
"""

import os
import json
import base64
from io import BytesIO
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from PIL import Image

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"

# Arquivos Oficiais do SIGSC (LiDAR MDT 1,0 m e Ortofoto 39 cm)
MDT_SIGSC_TIF = os.path.join(SIGSC_DIR, "raster", "mdt_sigsc", "MDT_SG-22-Z-D-I-3-SE-A.tif")
if not os.path.exists(MDT_SIGSC_TIF):
    MDT_SIGSC_TIF = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Exata.tif")

ORTO_SIGSC_TIF = os.path.join(SIGSC_DIR, "raster", "ortofoto_sigsc", "Orto-RGB_SG-22-Z-D-I-3-SE-A.tif")
if not os.path.exists(ORTO_SIGSC_TIF):
    ORTO_SIGSC_TIF = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Area_Estendida.tif")

HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_casa_arredores.html")


def main():
    print("=" * 80)
    print("GERANDO VISUALIZADOR 3D: CASA DO SÍTIO E ARREDORES (100% SIGSC OFICIAL)")
    print("=" * 80)

    # 1. Bounding box exata em coordenadas UTM SIRGAS 2000 22S (EPSG:31982)
    # Enquadra Casa, Salão, Quadra de Areia e Chalés 1 a 5 com margem de contexto
    left = 663280.0
    right = 663520.0   # 240,0 m de largura horizontal
    bottom = 6968540.0
    top = 6968720.0    # 180,0 m de comprimento horizontal

    width_m = float(right - left)
    height_m = float(top - bottom)
    cx_utm = float((left + right) / 2.0)  # 663400.0 m
    cy_utm = float((bottom + top) / 2.0)  # 6968630.0 m

    print(f"1. Janela Geográfica SIGSC:")
    print(f"   Dimensões: {width_m:.2f} m × {height_m:.2f} m")
    print(f"   Origem UTM: E [{left:.1f}, {right:.1f}], N [{bottom:.1f}, {top:.1f}]")
    print(f"   Centro do Modelo 3D: E {cx_utm:.2f}, N {cy_utm:.2f}")

    # 2. Extrai a Ortofoto Oficial do SIGSC (39 cm/px)
    print(f"\n2. Carregando Ortofoto Oficial SIGSC: {ORTO_SIGSC_TIF}")
    with rasterio.open(ORTO_SIGSC_TIF) as src_o:
        win_o = from_bounds(left, bottom, right, top, src_o.transform)
        rgb = src_o.read([1, 2, 3], window=win_o)
        img = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
        # Ajusta resolução com Lanczos para renderização nítida em WebGL
        w_px, h_px = img.size
        target_w = 1280
        target_h = int(h_px * (target_w / w_px))
        img_resized = img.resize((target_w, target_h), Image.LANCZOS)
        buf = BytesIO()
        img_resized.save(buf, format='JPEG', quality=90)
        b64_texture = base64.b64encode(buf.getvalue()).decode('ascii')
        print(f"   Textura SIGSC: {target_w}×{target_h} px ({len(b64_texture):,} caracteres base64)")

    # 3. Extrai o MDT LiDAR Oficial do SIGSC (1,0 m)
    print(f"\n3. Carregando MDT LiDAR 1,0 m Oficial SIGSC: {MDT_SIGSC_TIF}")
    with rasterio.open(MDT_SIGSC_TIF) as src_m:
        win_m = from_bounds(left, bottom, right, top, src_m.transform)
        elev_read = src_m.read(1, window=win_m)
        elev_raw = np.array(elev_read, dtype=np.float32)
        rows, cols = elev_raw.shape
        elev = elev_raw.copy()
        print(f"   Grade 3D LiDAR: {cols} colunas × {rows} linhas ({rows*cols:,} vértices métricos)")
        print(f"   Espaçamento real: {width_m/(cols-1):.2f} m × {height_m/(rows-1):.2f} m")
        print(f"   Cotas naturais SIGSC: Mínima = {elev.min():.2f} m, Máxima = {elev.max():.2f} m")

    # 4. Coordenadas Locais das Edificações (Origem no Centro da Janela)
    # Three.js: X = E - cx_utm; Z = -(N - cy_utm)
    casa_lx = float(663415.50 - cx_utm)      # +15.50 m
    casa_lz = float(-(6968636.50 - cy_utm))  #  -6.50 m
    salao_lx = float(663449.59 - cx_utm)     # +49.59 m
    salao_lz = float(-(6968652.91 - cy_utm)) # -22.91 m
    quadra_lx = float(663468.93 - cx_utm)    # +68.93 m
    quadra_lz = float(-(6968640.32 - cy_utm))# -10.32 m

    cota_casa = 540.95
    cota_salao = 547.10
    cota_quadra = 547.25

    # Malha de coordenadas métricas locais
    half_w = width_m / 2.0
    half_h = height_m / 2.0
    gy, gx = np.mgrid[0:rows, 0:cols]
    wx = -half_w + gx * (width_m / (cols - 1))
    wz = -half_h + gy * (height_m / (rows - 1))

    elev_final = elev.copy()
    rot_deg = 31.02
    rot_rad = float(np.radians(rot_deg))
    cos_a, sin_a = np.cos(rot_rad), np.sin(rot_rad)

    # 4.1 Platô e Terraplenagem do Salão 12x8m (Corte na Encosta)
    dx_s = wx - salao_lx
    dz_s = wz - salao_lz
    lx_s = dx_s * cos_a + dz_s * sin_a
    lz_s = -dx_s * sin_a + dz_s * cos_a
    in_salao = (np.abs(lx_s) <= 6.3) & (np.abs(lz_s) <= 4.3)
    elev_final[in_salao] = 547.05

    # 4.2 Platô da Quadra de Areia 22x12m
    dx_q = wx - quadra_lx
    dz_q = wz - quadra_lz
    lx_q = dx_q * cos_a + dz_q * sin_a
    lz_q = -dx_q * sin_a + dz_q * cos_a
    in_quadra = (np.abs(lx_q) <= 11.3) & (np.abs(lz_q) <= 6.3)
    elev_final[in_quadra] = cota_quadra

    # ATENÇÃO CRÍTICA: SOB A CASA DO SÍTIO, NENHUM PLATÔ ARTIFICIAL É APLICADO!
    # O terreno natural de bare-earth LiDAR do SIGSC flui suavemente, eliminando
    # qualquer elevação ou montículo artificial sob a residência.
    print(f"\n4. Nivelamento:")
    print(f"   Salão 12x8m: Platô de corte em 547,05 m")
    print(f"   Quadra 22x12m: Platô de areia em 547,25 m")
    print(f"   Casa do Sítio: TERRENO NATURAL PRESERVADO (zero montículo / zero elevação artificial)")

    # 5. Normalização Uint16 para Three.js
    z_min = float(elev_final.min())
    z_max = float(elev_final.max())
    z_range = float(z_max - z_min)
    u16_elev = ((elev_final - z_min) / z_range * 65535.0).clip(0, 65535).astype(np.uint16)
    b64_elev = base64.b64encode(u16_elev.tobytes()).decode('ascii')

    # Cotas relativas no espaço 3D (Y local do Three.js)
    casa_base_y = float(cota_casa - z_min)
    salao_base_y = float(cota_salao - z_min)
    quadra_base_y = float(cota_quadra - z_min)

    # Chalés 1 a 5
    chales_data = [
        {"id": 1, "utm": [663457.29, 6968674.96], "cota": 544.50},
        {"id": 2, "utm": [663448.54, 6968667.08], "cota": 545.20},
        {"id": 3, "utm": [663438.93, 6968659.26], "cota": 545.90},
        {"id": 4, "utm": [663466.65, 6968618.00], "cota": 542.80},
        {"id": 5, "utm": [663469.69, 6968600.54], "cota": 541.60}
    ]
    for c in chales_data:
        c["lx"] = round(float(c["utm"][0] - cx_utm), 2)
        c["lz"] = round(float(-(c["utm"][1] - cy_utm)), 2)
        c["base_y"] = round(float(c["cota"] - z_min), 2)

    chales_json = json.dumps(chales_data)

    print(f"\n5. Cotas 3D Relativas (Z_MIN = {z_min:.2f} m):")
    print(f"   Casa do Sítio (540,95 m): Y = {casa_base_y:.2f} m")
    print(f"   Salão 12x8m   (547,10 m): Y = {salao_base_y:.2f} m")
    print(f"   Quadra 22x12m (547,25 m): Y = {quadra_base_y:.2f} m")

    # 6. Montagem do HTML completo com visualizador de alta fidelidade
    html_code = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Casa do Sítio e Arredores — 100% SIGSC Oficial (LiDAR 1,0 m & Ortofoto)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      overflow: hidden;
      background: #090d16;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #f8fafc;
    }}
    #canvas-container {{ width: 100vw; height: 100vh; }}

    /* Painel Principal Flutuante */
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 360px;
      background: rgba(13, 19, 33, 0.94); color: #f8fafc; padding: 18px;
      border-radius: 14px; box-shadow: 0 16px 45px rgba(0,0,0,0.75);
      border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(16px);
      z-index: 10; max-height: calc(100vh - 32px); overflow-y: auto;
    }}
    h1 {{ font-size: 16px; font-weight: 700; color: #38bdf8; margin-bottom: 3px; display: flex; align-items: center; gap: 8px; }}
    .subtitle {{ font-size: 11.5px; color: #94a3b8; margin-bottom: 10px; }}
    .badges {{ display: flex; gap: 6px; margin-bottom: 12px; }}
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
      font-size: 11px; margin-top: 7px; color: #cbd5e1;
    }}
    .toggle-row input {{ cursor: pointer; accent-color: #38bdf8; }}

    /* Slider de Escala Z */
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

    /* Medição 3D */
    #measurer-box {{
      margin-top: 10px; padding: 10px; background: rgba(56, 189, 248, 0.1);
      border: 1px dashed #38bdf8; border-radius: 8px; font-size: 11px;
    }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="canvas-container"></div>

  <div id="panel">
    <h1>🏠 Casa do Sítio e Arredores</h1>
    <div class="subtitle">Sítio das Andorinhas — 100% SIGSC Nativo (Sem Dados de Drones)</div>
    <div class="badges">
      <span class="badge badge-sigsc">MDT LiDAR 1,0 m SIGSC</span>
      <span class="badge">Ortofoto SIGSC</span>
      <span class="badge badge-scale">Escala 1:1</span>
    </div>

    <div class="stat-row"><span class="stat-lbl">Extensão Focal:</span><span class="stat-val">{width_m:.1f} m × {height_m:.1f} m</span></div>
    <div class="stat-row"><span class="stat-lbl">Malha 3D Real:</span><span class="stat-val">{cols} × {rows} ({rows*cols:,} pts de 1m)</span></div>
    <div class="stat-row"><span class="stat-lbl">Casa do Sítio:</span><span class="stat-val">Piso 540,95m | Telhado KMZ 1 & 2</span></div>
    <div class="stat-row"><span class="stat-lbl">Salão de Eventos:</span><span class="stat-val">547,10m | Aberto (Sem Paredes)</span></div>
    <div class="stat-row"><span class="stat-lbl">Usina Solar Salão:</span><span class="stat-val">18 Módulos (10,44 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Quadra de Areia:</span><span class="stat-val">22 × 12 m (Cota 547,25 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">Chalés 1 a 5:</span><span class="stat-val">541,60 m a 545,90 m</span></div>

    <!-- Controle de Escala Z (1:1 Estrito) -->
    <div class="slider-box">
      <div class="slider-row">
        <span>⛰️ Escala Vertical (Z):</span>
        <span class="slider-val" id="lblZScale">1.00x (Real 1:1)</span>
      </div>
      <input type="range" id="sliderZScale" min="0.2" max="2.0" step="0.05" value="1.0" oninput="setZScale(this.value)">
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 3px; margin-top: 5px;">
        <button class="btn" style="padding: 2px 0; font-size: 9px;" onclick="setZScalePreset(0.5)">0.5x</button>
        <button class="btn" style="padding: 2px 0; font-size: 9px;" onclick="setZScalePreset(0.75)">0.75x</button>
        <button class="btn" style="padding: 2px 0; font-size: 9px; background: #065f46; border-color: #10b981;" onclick="setZScalePreset(1.0)">1.0x (1:1)</button>
        <button class="btn" style="padding: 2px 0; font-size: 9px;" onclick="setZScalePreset(1.5)">1.5x</button>
      </div>
    </div>

    <!-- Opções da Cobertura do Salão (Recuperadas) -->
    <div class="section-title">
      <span>Cobertura Salão 12×8m</span>
      <span style="font-size: 9.5px; color: #f59e0b;">Sem Paredes</span>
    </div>
    <div class="btn-group">
      <button class="btn active" id="btnOpt1" onclick="setSalaoOption(1)">🪵 1. Madeira Rústica</button>
      <button class="btn" id="btnOpt2" onclick="setSalaoOption(2)">🏗️ 2. Metálica 2 Águas</button>
      <button class="btn" id="btnOpt3" onclick="setSalaoOption(3)">📐 3. Telhado 1 Água</button>
      <button class="btn" id="btnOpt4" onclick="setSalaoOption(4)">⚽ 4. Refletores Arena</button>
    </div>

    <!-- Câmeras Rápidas -->
    <div class="section-title">Câmeras & Perspectivas 3D (1:1)</div>
    <div class="btn-group">
      <button class="btn" onclick="goToView('casa')">🏠 Casa do Sítio</button>
      <button class="btn" onclick="goToView('salao')">🏛️ No Salão</button>
      <button class="btn" onclick="goToView('quadra')">🏐 Na Quadra</button>
      <button class="btn" onclick="goToView('chales')">🏡 Chalés 1 a 5</button>
      <button class="btn btn-full" onclick="goToView('panoramica')">🌐 Panorâmica Geral</button>
      <button class="btn btn-full" onclick="goToView('pedestre')">🚶 Nível do Pedestre (Olhos 1,70m)</button>
    </div>

    <!-- Camadas & Ferramentas -->
    <div class="section-title">Camadas & Ferramentas</div>
    <div class="toggle-row">
      <span>Exibir Edificações 3D</span>
      <input type="checkbox" id="chk-edif" checked onchange="toggleEdif(this.checked)">
    </div>
    <div class="toggle-row">
      <span>Malha de Relevo (Wireframe 1m)</span>
      <input type="checkbox" id="chk-wire" onchange="toggleWire(this.checked)">
    </div>
    <div class="toggle-row">
      <span>Réguas Métricas 1:1 (Grades 1m×1m)</span>
      <input type="checkbox" id="chk-rulers" checked onchange="toggleRulers(this.checked)">
    </div>
    <div class="toggle-row">
      <span>Ferramenta Trena / Medição 3D</span>
      <input type="checkbox" id="chk-ruler-tool" onchange="toggleMeasureTool(this.checked)">
    </div>

    <div id="measurer-box" style="display:none;">
      <strong>📏 Trena Interativa 3D:</strong><br>
      Clique em dois pontos no relevo ou construções para medir distância horizontal, vertical e diagonal real.
      <div id="meas-result" style="margin-top: 4px; color: #4ade80; font-weight: 700;">Aguardando cliques...</div>
    </div>
  </div>

  <script>
    // =========================================================================
    // 1. CONSTANTES E DADOS GEORREFERENCIADOS (SIGSC 100% NATIVO)
    // =========================================================================
    const WIDTH_M = {width_m:.4f};
    const HEIGHT_M = {height_m:.4f};
    const COLS = {cols};
    const ROWS = {rows};
    const Z_MIN = {z_min:.4f};
    const Z_MAX = {z_max:.4f};
    const Z_RANGE = {z_range:.4f};
    const CX_UTM = {cx_utm:.2f};
    const CY_UTM = {cy_utm:.2f};

    const casaData = {{
      lx: {casa_lx:.2f},
      lz: {casa_lz:.2f},
      base_y: {casa_base_y:.2f},
      cota_piso: {cota_casa:.2f},
      cx_utm: 663415.50,
      cy_utm: 6968636.50
    }};

    const salaoData = {{
      lx: {salao_lx:.2f},
      lz: {salao_lz:.2f},
      base_y: {salao_base_y:.2f},
      cota_piso: {cota_salao:.2f},
      rot_rad: {rot_rad:.6f}
    }};

    const quadraData = {{
      lx: {quadra_lx:.2f},
      lz: {quadra_lz:.2f},
      base_y: {quadra_base_y:.2f},
      cota_areia: {cota_quadra:.2f},
      rot_rad: {rot_rad:.6f}
    }};

    const chalesData = {chales_json};

    // =========================================================================
    // 2. INICIALIZAÇÃO DA CENA THREE.JS (PROPORÇÃO MÉTRICA 1:1 ESTRITA)
    // =========================================================================
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d16);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.5, 3000);
    // Posiciona câmera inicial visando a Casa do Sítio e Salão
    camera.position.set(casaData.lx + 42, casaData.base_y + 32, casaData.lz + 46);

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
    controls.target.set(casaData.lx, casaData.base_y + 2, casaData.lz);
    controls.update();

    // Iluminação Solar Realista
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.85);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfff8e7, 1.35);
    sunLight.position.set(130, casaData.base_y + 140, 110);
    sunLight.target.position.set(casaData.lx, casaData.base_y, casaData.lz);
    scene.add(sunLight.target);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 400;
    sunLight.shadow.camera.left = -120;
    sunLight.shadow.camera.right = 120;
    sunLight.shadow.camera.top = 120;
    sunLight.shadow.camera.bottom = -120;
    scene.add(sunLight);

    // =========================================================================
    // 3. TERRENO 3D COM MDT LIDAR 1,0 m & TEXTURA ORTOFOTO SIGSC
    // =========================================================================
    const b64Elev = "{b64_elev}";
    const binStr = atob(b64Elev);
    const u16Arr = new Uint16Array(binStr.length / 2);
    for (let i = 0; i < u16Arr.length; i++) {{
      u16Arr[i] = binStr.charCodeAt(i * 2) | (binStr.charCodeAt(i * 2 + 1) << 8);
    }}

    const geom = new THREE.PlaneGeometry(WIDTH_M, HEIGHT_M, COLS - 1, ROWS - 1);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    const baseElevations = new Float32Array(pos.count);
    for (let r = 0; r < ROWS; r++) {{
      for (let c = 0; c < COLS; c++) {{
        const idx = r * COLS + c;
        const norm = u16Arr[idx] / 65535.0;
        const yVal = norm * Z_RANGE;
        baseElevations[idx] = yVal;
        pos.setY(idx, yVal);
      }}
    }}
    geom.computeVertexNormals();

    const texImg = new Image();
    const tex = new THREE.Texture();
    texImg.onload = function() {{
      tex.image = texImg;
      tex.needsUpdate = true;
    }};
    texImg.src = "data:image/jpeg;base64,{b64_texture}";

    const terrainMat = new THREE.MeshStandardMaterial({{
      map: tex,
      roughness: 0.88,
      metalness: 0.04,
      flatShading: false
    }});
    const terrainMesh = new THREE.Mesh(geom, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // Wireframe de 1m para comprovação geométrica
    const wireMat = new THREE.MeshBasicMaterial({{
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
      visible: false
    }});
    const wireMesh = new THREE.Mesh(geom, wireMat);
    scene.add(wireMesh);

    // Grupo de Edificações 3D
    const edifGroup = new THREE.Group();
    scene.add(edifGroup);

    // =========================================================================
    // 4. TEXTURA PROCEDURAL DE TELHAS DE BARRO COLONIAIS EXISTENTES
    // =========================================================================
    function createClayTileTextures() {{
      const w = 512, h = 512;
      const cDiff = document.createElement('canvas');
      cDiff.width = w; cDiff.height = h;
      const ctx = cDiff.getContext('2d');

      const cBump = document.createElement('canvas');
      cBump.width = w; cBump.height = h;
      const ctxB = cBump.getContext('2d');

      const numCols = 8;
      const numRows = 6;
      const colW = w / numCols;
      const rowH = h / numRows;

      const imgD = ctx.createImageData(w, h);
      const d = imgD.data;
      const imgB = ctxB.createImageData(w, h);
      const b = imgB.data;

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
      ctx.putImageData(imgD, 0, 0);
      ctxB.putImageData(imgB, 0, 0);

      const mapTex = new THREE.CanvasTexture(cDiff);
      mapTex.wrapS = THREE.RepeatWrapping; mapTex.wrapT = THREE.RepeatWrapping;

      const bumpTex = new THREE.CanvasTexture(cBump);
      bumpTex.wrapS = THREE.RepeatWrapping; bumpTex.wrapT = THREE.RepeatWrapping;

      return {{ mapTex, bumpTex }};
    }}

    const clayTextures = createClayTileTextures();

    // =========================================================================
    // 5. CASA DO SÍTIO: TELHADO 1 & TELHADO 2 RIGOROSAMENTE ALINHADOS AOS KMZ
    // =========================================================================
    const casaGroup = new THREE.Group();
    casaGroup.position.set(casaData.lx, casaData.base_y, casaData.lz);
    edifGroup.add(casaGroup);

    (function buildCasaSitioKMZ() {{
      const cxU = casaData.cx_utm;
      const cyU = casaData.cy_utm;

      // Cumeeira Central Compartilhada (Extremidades Sul e Norte)
      const Rs = [663412.325, 6968630.679];
      const Rn = [663415.673, 6968642.764];

      // Vetores unitários da cumeeira (longitudinal e perpendicular Leste)
      const uE = 0.266982, uN = 0.963702;  // ao longo da cumeeira (N-NE)
      const nE = 0.963702, nN = -0.266982; // perpendicular leste (E-SE)

      const H_RIDGE = 4.60;   // Altura da cumeeira sobre o piso (m)
      const S_WEST = 0.34;    // Inclinação 34% na Ala Oeste (Telhado 1)
      const S_EAST = 0.235;   // Inclinação 23,5% na Ala Leste (Telhado 2)

      function roofMetrics(e, n) {{
        const along = (e - Rs[0]) * uE + (n - Rs[1]) * uN;
        const perp = (e - Rs[0]) * nE + (n - Rs[1]) * nN;
        const h = (perp <= 0)
          ? (H_RIDGE - S_WEST * Math.abs(perp))
          : (H_RIDGE - S_EAST * perp);
        return {{
          lx: e - cxU,
          lz: -(n - cyU),
          along: along,
          perp: perp,
          h: h
        }};
      }}

      // Vértices Exatos de telhado1.kmz (Ala Oeste - 6 vértices)
      const t1UTM = [
        [663408.675, 6968631.318],
        Rs,
        Rn,
        [663411.349, 6968643.959],
        [663409.719, 6968639.167],
        [663410.819, 6968638.844]
      ];
      const t1Tris = [[0, 1, 5], [1, 2, 5], [5, 2, 4], [2, 3, 4]];

      // Vértices Exatos de telhado2.kmz (Ala Leste - 6 vértices)
      const t2UTM = [
        Rs,
        [663417.808, 6968628.888],
        [663420.069, 6968635.545],
        [663421.641, 6968635.100],
        [663423.051, 6968640.760],
        Rn
      ];
      const t2Tris = [[0, 1, 2], [0, 2, 5], [2, 3, 5], [3, 4, 5]];

      const casaClayMat = new THREE.MeshStandardMaterial({{
        map: clayTextures.mapTex,
        bumpMap: clayTextures.bumpTex,
        bumpScale: 0.075,
        roughness: 0.72,
        metalness: 0.04,
        side: THREE.DoubleSide
      }});
      const casaWoodSoffitMat = new THREE.MeshStandardMaterial({{ color: 0x5c2d16, roughness: 0.8, side: THREE.DoubleSide }});
      const casaWallMat = new THREE.MeshStandardMaterial({{ color: 0xf8fafc, roughness: 0.78, side: THREE.DoubleSide }});
      const casaPlinthMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.85, side: THREE.DoubleSide }});
      const casaTrimMat = new THREE.MeshStandardMaterial({{ color: 0x452311, roughness: 0.7 }});
      const casaGlassMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.15, metalness: 0.8 }});
      const ridgeTileMat = new THREE.MeshStandardMaterial({{ color: 0x9a3b14, roughness: 0.68 }});

      function buildRoofSlopeMesh(ptsUTM, tris, isEast) {{
        const thickness = 0.14;
        const posArr = [];
        const uvsArr = [];
        const pts = ptsUTM.map(p => roofMetrics(p[0], p[1]));

        function pushTri(pA, pB, pC, yOff) {{
          posArr.push(pA.lx, pA.h + yOff, pA.lz);
          posArr.push(pB.lx, pB.h + yOff, pB.lz);
          posArr.push(pC.lx, pC.h + yOff, pC.lz);
          uvsArr.push(pA.along / 1.6, Math.abs(pA.perp) / 1.5);
          uvsArr.push(pB.along / 1.6, Math.abs(pB.perp) / 1.5);
          uvsArr.push(pC.along / 1.6, Math.abs(pC.perp) / 1.5);
        }}

        tris.forEach(t => {{
          pushTri(pts[t[0]], pts[t[1]], pts[t[2]], thickness);
        }});

        const topGeom = new THREE.BufferGeometry();
        topGeom.setAttribute('position', new THREE.Float32BufferAttribute(posArr, 3));
        topGeom.setAttribute('uv', new THREE.Float32BufferAttribute(uvsArr, 2));
        topGeom.computeVertexNormals();
        const topMesh = new THREE.Mesh(topGeom, casaClayMat);
        topMesh.castShadow = true;
        topMesh.receiveShadow = true;
        casaGroup.add(topMesh);

        // Forro inferior de madeira
        const botPos = [];
        tris.forEach(t => {{
          const pA = pts[t[0]], pB = pts[t[2]], pC = pts[t[1]];
          botPos.push(pA.lx, pA.h, pA.lz, pB.lx, pB.h, pB.lz, pC.lx, pC.h, pC.lz);
        }});
        for (let i = 0; i < pts.length; i++) {{
          const p1 = pts[i], p2 = pts[(i + 1) % pts.length];
          botPos.push(
            p1.lx, p1.h, p1.lz, p2.lx, p2.h, p2.lz, p2.lx, p2.h + thickness, p2.lz,
            p1.lx, p1.h, p1.lz, p2.lx, p2.h + thickness, p2.lz, p1.lx, p1.h + thickness, p1.lz
          );
        }}
        const botGeom = new THREE.BufferGeometry();
        botGeom.setAttribute('position', new THREE.Float32BufferAttribute(botPos, 3));
        botGeom.computeVertexNormals();
        const botMesh = new THREE.Mesh(botGeom, casaWoodSoffitMat);
        botMesh.castShadow = true;
        casaGroup.add(botMesh);

        // Nervuras de telhas capa e bica reais (34 linhas por água)
        const numRibs = 34;
        for (let r = 0; r <= numRibs; r++) {{
          const alongPos = (r / numRibs) * 12.50;
          let maxPerp = 0;
          if (!isEast) {{
            maxPerp = (alongPos >= 7.48) ? -4.55 : -3.66;
          }} else {{
            maxPerp = (alongPos >= 6.75) ? 7.72 : 5.96;
          }}
          const eStart = Rs[0] + alongPos * uE;
          const nStart = Rs[1] + alongPos * uN;
          const eEnd = eStart + maxPerp * nE;
          const nEnd = nStart + maxPerp * nN;
          const mStart = roofMetrics(eStart, nStart);
          const mEnd = roofMetrics(eEnd, nEnd);

          const dx = mEnd.lx - mStart.lx;
          const dy = mEnd.h - mStart.h;
          const dz = mEnd.lz - mStart.lz;
          const ribLen = Math.hypot(dx, dy, dz);

          const ribGeom = new THREE.CylinderGeometry(0.055, 0.065, ribLen, 6, 1, false, 0, Math.PI);
          const ribMesh = new THREE.Mesh(ribGeom, ridgeTileMat);
          ribMesh.position.set(
            (mStart.lx + mEnd.lx) * 0.5,
            (mStart.h + mEnd.h) * 0.5 + thickness + 0.01,
            (mStart.lz + mEnd.lz) * 0.5
          );
          const dirVec = new THREE.Vector3(dx, dy, dz).normalize();
          ribMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dirVec);
          ribMesh.castShadow = true;
          casaGroup.add(ribMesh);
        }}
      }}

      buildRoofSlopeMesh(t1UTM, t1Tris, false);
      buildRoofSlopeMesh(t2UTM, t2Tris, true);

      // Cumeeira Central Cilindrica com Capas Cerâmicas
      const mRs = roofMetrics(Rs[0], Rs[1]);
      const mRn = roofMetrics(Rn[0], Rn[1]);
      const rDx = mRn.lx - mRs.lx;
      const rDz = mRn.lz - mRs.lz;
      const rLen = Math.hypot(rDx, rDz);
      const ridgeDir = new THREE.Vector3(rDx, 0, rDz).normalize();

      const mainRidgeGeom = new THREE.CylinderGeometry(0.15, 0.15, rLen + 0.25, 14);
      const mainRidgeMesh = new THREE.Mesh(mainRidgeGeom, ridgeTileMat);
      mainRidgeMesh.position.set((mRs.lx + mRn.lx) * 0.5, H_RIDGE + 0.18, (mRs.lz + mRn.lz) * 0.5);
      mainRidgeMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), ridgeDir);
      mainRidgeMesh.castShadow = true;
      casaGroup.add(mainRidgeMesh);

      const numCapas = Math.floor(rLen / 0.38);
      for (let k = 0; k <= numCapas; k++) {{
        const t = k / numCapas;
        const ringGeom = new THREE.CylinderGeometry(0.17, 0.155, 0.14, 12);
        const ringMesh = new THREE.Mesh(ringGeom, ridgeTileMat);
        ringMesh.position.set(
          mRs.lx + rDx * t,
          H_RIDGE + 0.185,
          mRs.lz + rDz * t
        );
        ringMesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), ridgeDir);
        casaGroup.add(ringMesh);
      }}

      // Paredes e Embasamento da Casa do Sítio
      const wallUTM = [
        [663412.43, 6968631.12],
        [663409.24, 6968631.68],
        [663411.37, 6968639.14],
        [663410.30, 6968639.47],
        [663411.64, 6968643.41],
        [663415.55, 6968642.33],
        [663422.51, 6968640.44],
        [663421.32, 6968635.66],
        [663419.78, 6968636.10],
        [663417.53, 6968629.46]
      ];
      const wallPts = wallUTM.map(p => roofMetrics(p[0], p[1]));

      const wallPos = [];
      const plinthPos = [];
      for (let i = 0; i < wallPts.length; i++) {{
        const p1 = wallPts[i];
        const p2 = wallPts[(i + 1) % wallPts.length];
        // Parede branca do piso (0.0) até o forro do telhado (h)
        wallPos.push(
          p1.lx, 0.0, p1.lz, p2.lx, 0.0, p2.lz, p2.lx, p2.h + 0.02, p2.lz,
          p1.lx, 0.0, p1.lz, p2.lx, p2.h + 0.02, p2.lz, p1.lx, p1.h + 0.02, p1.lz
        );
        // Embasamento de pedra/concreto descendo até -3,0m para fixação no terreno natural em declive
        plinthPos.push(
          p1.lx, -3.0, p1.lz, p2.lx, -3.0, p2.lz, p2.lx, 0.18, p2.lz,
          p1.lx, -3.0, p1.lz, p2.lx, 0.18, p2.lz, p1.lx, 0.18, p1.lz
        );
      }}

      const wallGeom = new THREE.BufferGeometry();
      wallGeom.setAttribute('position', new THREE.Float32BufferAttribute(wallPos, 3));
      wallGeom.computeVertexNormals();
      const wallMesh = new THREE.Mesh(wallGeom, casaWallMat);
      wallMesh.castShadow = true;
      wallMesh.receiveShadow = true;
      casaGroup.add(wallMesh);

      const plinthGeom = new THREE.BufferGeometry();
      plinthGeom.setAttribute('position', new THREE.Float32BufferAttribute(plinthPos, 3));
      plinthGeom.computeVertexNormals();
      const plinthMesh = new THREE.Mesh(plinthGeom, casaPlinthMat);
      plinthMesh.castShadow = true;
      plinthMesh.receiveShadow = true;
      casaGroup.add(plinthMesh);

      // Portas e Janelas Reais
      function addOpening(pA, pB, tAlong, wOpen, hOpen, yBottom, isDoor) {{
        const cx = pA.lx + (pB.lx - pA.lx) * tAlong;
        const cz = pA.lz + (pB.lz - pA.lz) * tAlong;
        const ang = Math.atan2(pB.lz - pA.lz, pB.lx - pA.lx);
        const frame = new THREE.Mesh(new THREE.BoxGeometry(wOpen, hOpen, 0.14), isDoor ? casaTrimMat : casaGlassMat);
        frame.position.set(cx, yBottom + hOpen * 0.5, cz);
        frame.rotation.y = -ang;
        casaGroup.add(frame);
        if (!isDoor) {{
          const border = new THREE.Mesh(new THREE.BoxGeometry(wOpen + 0.14, hOpen + 0.14, 0.10), casaTrimMat);
          border.position.set(cx, yBottom + hOpen * 0.5, cz);
          border.rotation.y = -ang;
          casaGroup.add(border);
        }}
      }}
      addOpening(wallPts[1], wallPts[2], 0.35, 1.40, 1.15, 1.00, false);
      addOpening(wallPts[1], wallPts[2], 0.75, 1.40, 1.15, 1.00, false);
      addOpening(wallPts[8], wallPts[9], 0.50, 1.50, 1.20, 1.00, false);
      addOpening(wallPts[6], wallPts[7], 0.50, 0.95, 2.10, 0.15, true);
      addOpening(wallPts[4], wallPts[5], 0.55, 1.30, 1.10, 1.05, false);
      addOpening(wallPts[5], wallPts[6], 0.45, 0.95, 2.10, 0.15, true);
    }})();

    // =========================================================================
    // 6. SALÃO DE FESTAS 12x8m RECUPERADO (ESTRUTURA ABERTA SEM PAREDES + USINA SOLAR)
    // =========================================================================
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salaoData.lx, salaoData.base_y, salaoData.lz);
    salaoGroup.rotation.y = -salaoData.rot_rad;
    edifGroup.add(salaoGroup);

    // Embasamento e Piso Cerâmico
    const foundationMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.85, metalness: 0.1 }});
    const salaoPlinth = new THREE.Mesh(new THREE.BoxGeometry(12.0, 2.50, 8.0), foundationMat);
    salaoPlinth.position.set(0, -1.13, 0);
    salaoPlinth.receiveShadow = true;
    salaoPlinth.castShadow = true;
    salaoGroup.add(salaoPlinth);

    const floorTileMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.5 }});
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.1, 0.15, 8.1), floorTileMat);
    salaoFloor.position.set(0, 0.125, 0);
    salaoFloor.receiveShadow = true;
    salaoGroup.add(salaoFloor);

    // Blocos de Fundação dos Pilares
    const footingMat = new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.9 }});
    const pilarPositions = [
      [-5.7, 1.85, -3.7], [0, 1.85, -3.7], [5.7, 1.85, -3.7],
      [-5.7, 1.85, 3.7],  [0, 1.85, 3.7],  [5.7, 1.85, 3.7]
    ];
    pilarPositions.forEach(p => {{
      const footing = new THREE.Mesh(new THREE.BoxGeometry(0.5, 2.6, 0.5), footingMat);
      footing.position.set(p[0], -1.1, p[2]);
      footing.castShadow = true;
      salaoGroup.add(footing);
    }});

    // Escada de Acesso Frontal
    const stairMat = new THREE.MeshStandardMaterial({{ color: 0x78716c, roughness: 0.7 }});
    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), stairMat);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      step.receiveShadow = true;
      salaoGroup.add(step);
    }}

    // Muro de Arrimo de Corte nos Fundos do Salão
    const cutWallMat = new THREE.MeshStandardMaterial({{ color: 0x57534e, roughness: 0.9 }});
    const cutRetainingWall = new THREE.Mesh(new THREE.BoxGeometry(14.0, 1.60, 0.40), cutWallMat);
    cutRetainingWall.position.set(0, 0.30, -5.2);
    cutRetainingWall.castShadow = true;
    salaoGroup.add(cutRetainingWall);

    // Canaleta de Drenagem Superior
    const ditchMat = new THREE.MeshStandardMaterial({{ color: 0x3f3f46, roughness: 0.8 }});
    const ditch = new THREE.Mesh(new THREE.BoxGeometry(14.0, 0.15, 0.50), ditchMat);
    ditch.position.set(0, -0.40, -4.6);
    salaoGroup.add(ditch);

    // Grupos das 4 Opções Arquitetônicas
    const optGroup1 = new THREE.Group();
    const optGroup2 = new THREE.Group();
    const optGroup3 = new THREE.Group();
    const optGroup4 = new THREE.Group();
    salaoGroup.add(optGroup1, optGroup2, optGroup3);
    scene.add(optGroup4);

    // --- OPÇÃO 1: MADEIRA RÚSTICA (2 ÁGUAS) + TELHAS DE BARRO + USINA SOLAR ---
    const salaoClayMap = clayTextures.mapTex.clone();
    salaoClayMap.needsUpdate = true;
    salaoClayMap.repeat.set(6.5, 2.5);
    const salaoClayBump = clayTextures.bumpTex.clone();
    salaoClayBump.needsUpdate = true;
    salaoClayBump.repeat.set(6.5, 2.5);

    const rusticWoodMat = new THREE.MeshStandardMaterial({{ color: 0x452311, roughness: 0.85 }});
    const tileCeramicMat = new THREE.MeshStandardMaterial({{
      map: salaoClayMap,
      bumpMap: salaoClayBump,
      bumpScale: 0.06,
      roughness: 0.72,
      metalness: 0.04
    }});

    pilarPositions.forEach(p => {{
      const pMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 3.6, 12), rusticWoodMat);
      pMesh.position.set(p[0], 1.8, p[2]);
      pMesh.castShadow = true;
      optGroup1.add(pMesh);
    }});

    const vigaMaster1 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.4, 12), rusticWoodMat);
    vigaMaster1.rotation.z = Math.PI / 2; vigaMaster1.position.set(0, 3.65, -3.7);
    const vigaMaster2 = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 12.4, 12), rusticWoodMat);
    vigaMaster2.rotation.z = Math.PI / 2; vigaMaster2.position.set(0, 3.65, 3.7);
    optGroup1.add(vigaMaster1, vigaMaster2);

    [-5.7, 0, 5.7].forEach(x => {{
      const truss = new THREE.Group();
      truss.position.set(x, 0, 0);
      const tieBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 8.2, 10), rusticWoodMat);
      tieBeam.rotation.x = Math.PI / 2; tieBeam.position.set(0, 3.65, 0);
      truss.add(tieBeam);
      const kingPost = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 1.40, 10), rusticWoodMat);
      kingPost.position.set(0, 4.35, 0);
      truss.add(kingPost);
      const rafterLen = 4.35;
      const angleRafter = Math.atan2(1.50, 4.0);
      const rafterN = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, rafterLen, 10), rusticWoodMat);
      rafterN.rotation.x = -angleRafter; rafterN.position.set(0, 4.40, -2.0);
      truss.add(rafterN);
      const rafterS = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, rafterLen, 10), rusticWoodMat);
      rafterS.rotation.x = angleRafter; rafterS.position.set(0, 4.40, 2.0);
      truss.add(rafterS);
      optGroup1.add(truss);
    }});

    const ridgeBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 13.2, 12), rusticWoodMat);
    ridgeBeam.rotation.z = Math.PI / 2;
    ridgeBeam.position.set(0, 5.15, 0);
    optGroup1.add(ridgeBeam);

    const roofSlopeBack = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofSlopeBack.rotation.x = -THREE.MathUtils.degToRad(21.8);
    roofSlopeBack.position.set(0, 4.45, -2.18);
    roofSlopeBack.castShadow = true;

    const roofSlopeFront = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofSlopeFront.rotation.x = THREE.MathUtils.degToRad(21.8);
    roofSlopeFront.position.set(0, 4.45, 2.18);
    roofSlopeFront.castShadow = true;
    optGroup1.add(roofSlopeBack, roofSlopeFront);

    // Cumeeira Cerâmica
    const salaoRidgeCap = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 13.3, 16), new THREE.MeshStandardMaterial({{ color: 0x9a3b14, roughness: 0.68 }}));
    salaoRidgeCap.rotation.z = Math.PI / 2;
    salaoRidgeCap.position.set(0, 5.28, 0);
    salaoRidgeCap.castShadow = true;
    optGroup1.add(salaoRidgeCap);

    // Usina Solar Fotovoltaica na Cobertura (18 Módulos de 580W = 10,44 kWp)
    const solarFrameMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 }});
    const solarCellMat = new THREE.MeshStandardMaterial({{ color: 0x0f172a, metalness: 0.95, roughness: 0.12 }});
    const solarModGroup = new THREE.Group();
    solarModGroup.rotation.x = THREE.MathUtils.degToRad(21.8);
    solarModGroup.position.set(0, 4.54, 2.18);

    for (let row = 0; row < 2; row++) {{
      for (let col = 0; col < 9; col++) {{
        const mod = new THREE.Group();
        mod.position.set(-5.0 + col * 1.25, 0.05, -1.1 + row * 2.2);
        const frame = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.04, 2.05), solarFrameMat);
        const cell = new THREE.Mesh(new THREE.BoxGeometry(1.11, 0.045, 2.01), solarCellMat);
        mod.add(frame, cell);
        solarModGroup.add(mod);
      }}
    }}
    optGroup1.add(solarModGroup);

    // --- OPÇÃO 2: ESTRUTURA METÁLICA ---
    const steelDarkMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, metalness: 0.8, roughness: 0.3 }});
    const panelSandwichMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.5, roughness: 0.4 }});

    pilarPositions.forEach(p => {{
      const pSteel = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3.6, 0.2), steelDarkMat);
      pSteel.position.set(p[0], 1.8, p[2]);
      pSteel.castShadow = true;
      optGroup2.add(pSteel);
    }});

    const steelBeam1 = new THREE.Mesh(new THREE.BoxGeometry(12.4, 0.22, 0.15), steelDarkMat);
    steelBeam1.position.set(0, 3.6, -3.7);
    const steelBeam2 = new THREE.Mesh(new THREE.BoxGeometry(12.4, 0.22, 0.15), steelDarkMat);
    steelBeam2.position.set(0, 3.6, 3.7);
    optGroup2.add(steelBeam1, steelBeam2);

    [-5.7, 0, 5.7].forEach(x => {{
      const mTruss = new THREE.Group();
      mTruss.position.set(x, 0, 0);
      const bot = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.12, 8.0), steelDarkMat);
      bot.position.set(0, 3.6, 0); mTruss.add(bot);
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.95, 0.08), steelDarkMat);
      post.position.set(0, 4.07, 0); mTruss.add(post);
      optGroup2.add(mTruss);
    }});

    const roofSteelBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofSteelBack.position.set(0, 4.35, -2.15);
    roofSteelBack.castShadow = true;
    const roofSteelFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofSteelFront.position.set(0, 4.35, 2.15);
    roofSteelFront.castShadow = true;
    const steelRidgeRufo = new THREE.Mesh(new THREE.BoxGeometry(12.9, 0.06, 0.35), steelDarkMat);
    steelRidgeRufo.position.set(0, 5.05, 0);
    optGroup2.add(roofSteelBack, roofSteelFront, steelRidgeRufo);

    // --- OPÇÃO 3: TELHADO 1 ÁGUA (DECLIVE COM A ENCOSTA) ---
    [-5.7, 0, 5.7].forEach(x => {{
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.3, 0.2), steelDarkMat);
      pBack.position.set(x, 2.15, -3.7); pBack.castShadow = true; optGroup3.add(pBack);
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3.0, 0.2), steelDarkMat);
      pFront.position.set(x, 1.5, 3.7); pFront.castShadow = true; optGroup3.add(pFront);
    }});
    const roofMonoGroup = new THREE.Group();
    roofMonoGroup.position.set(0, 3.65, 0);
    const roofMono = new THREE.Mesh(new THREE.BoxGeometry(13.0, 0.12, 9.4), panelSandwichMat);
    roofMono.rotation.x = THREE.MathUtils.degToRad(9.3);
    roofMono.position.set(0, 0.65, 0);
    roofMono.castShadow = true;
    roofMonoGroup.add(roofMono);
    optGroup3.add(roofMonoGroup);

    // --- OPÇÃO 4: REFLETORES ARENA NOTURNA NA QUADRA ---
    const floodlights = [];
    const poleMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.8, roughness: 0.2 }});
    const towerPositions = [
      [quadraData.lx - 11.5, quadraData.base_y, quadraData.lz - 6.5],
      [quadraData.lx + 11.5, quadraData.base_y, quadraData.lz - 6.5],
      [quadraData.lx - 11.5, quadraData.base_y, quadraData.lz + 6.5],
      [quadraData.lx + 11.5, quadraData.base_y, quadraData.lz + 6.5]
    ];
    towerPositions.forEach(posT => {{
      const tower = new THREE.Group();
      tower.position.set(posT[0], posT[1], posT[2]);
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.18, 7.5, 12), poleMat);
      pole.position.set(0, 3.75, 0);
      tower.add(pole);
      const crossbar = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.08, 0.08), poleMat);
      crossbar.position.set(0, 7.4, 0);
      tower.add(crossbar);

      const spot = new THREE.SpotLight(0xffffff, 0.0);
      spot.position.set(0, 7.4, 0);
      spot.angle = Math.PI / 4.2;
      spot.penumbra = 0.4;
      spot.decay = 1.5;
      spot.distance = 45;
      spot.castShadow = true;
      spot.target.position.set(quadraData.lx, quadraData.base_y, quadraData.lz);
      scene.add(spot.target);
      tower.add(spot);
      floodlights.push(spot);
      optGroup4.add(tower);
    }});

    optGroup1.visible = true;
    optGroup2.visible = false;
    optGroup3.visible = false;

    // =========================================================================
    // 7. QUADRA DE AREIA 22x12m
    // =========================================================================
    const quadraGroup = new THREE.Group();
    quadraGroup.position.set(quadraData.lx, quadraData.base_y, quadraData.lz);
    quadraGroup.rotation.y = -quadraData.rot_rad;
    edifGroup.add(quadraGroup);

    const sandMat = new THREE.MeshStandardMaterial({{ color: 0xfde047, roughness: 0.95 }});
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.30, 12.0), sandMat);
    sandMesh.position.y = 0.15;
    sandMesh.receiveShadow = true;
    quadraGroup.add(sandMesh);

    const bordaMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const bordaMesh = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.40, 12.3), bordaMat);
    bordaMesh.position.y = 0.20;
    quadraGroup.add(bordaMesh);

    const postMat = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, metalness: 0.7, roughness: 0.3 }});
    const quadraPostPositions = [
      [-11, -6], [-5.5, -6], [0, -6], [5.5, -6], [11, -6],
      [-11, 6], [-5.5, 6], [0, 6], [5.5, 6], [11, 6]
    ];
    quadraPostPositions.forEach(p => {{
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 6.0, 8), postMat);
      pole.position.set(p[0], 3.0, p[1]);
      pole.castShadow = true;
      quadraGroup.add(pole);
    }});

    const netMat = new THREE.MeshBasicMaterial({{ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.65 }});
    const net = new THREE.Mesh(new THREE.PlaneGeometry(8.5, 1.0), netMat);
    net.position.set(0, 2.2, 0);
    net.rotation.y = Math.PI / 2;
    quadraGroup.add(net);

    // =========================================================================
    // 8. CHALÉS 1 A 5 GEORREFERENCIADOS
    // =========================================================================
    const chaleWallMat = new THREE.MeshStandardMaterial({{ color: 0x78350f, roughness: 0.8 }});
    const chaleRoofMat = new THREE.MeshStandardMaterial({{ color: 0x9a3412, roughness: 0.7 }});
    const chaleGlassMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.2, metalness: 0.8 }});

    chalesData.forEach(c => {{
      const cGroup = new THREE.Group();
      cGroup.position.set(c.lx, c.base_y, c.lz);
      cGroup.rotation.y = -salaoData.rot_rad;

      // Base e Paredes de Madeira
      const body = new THREE.Mesh(new THREE.BoxGeometry(6.0, 2.8, 4.5), chaleWallMat);
      body.position.y = 1.4;
      body.castShadow = true;
      cGroup.add(body);

      // Telhado Duas Águas
      const rGeom = new THREE.BufferGeometry();
      const rPts = [
        -3.4, 2.7, -2.5, -3.4, 2.7, 2.5, 0.0, 4.2, 2.5,
        -3.4, 2.7, -2.5, 0.0, 4.2, 2.5, 0.0, 4.2, -2.5,
        0.0, 4.2, -2.5, 0.0, 4.2, 2.5, 3.4, 2.7, 2.5,
        0.0, 4.2, -2.5, 3.4, 2.7, 2.5, 3.4, 2.7, -2.5
      ];
      rGeom.setAttribute('position', new THREE.Float32BufferAttribute(rPts, 3));
      rGeom.computeVertexNormals();
      const rMesh = new THREE.Mesh(rGeom, chaleRoofMat);
      rMesh.castShadow = true;
      cGroup.add(rMesh);

      // Varanda Frontal
      const deck = new THREE.Mesh(new THREE.BoxGeometry(6.2, 0.15, 1.6), chaleWallMat);
      deck.position.set(0, 0.1, 3.0);
      cGroup.add(deck);

      // Janela Panorâmica
      const win = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 1.2), chaleGlassMat);
      win.position.set(0, 1.5, 2.26);
      cGroup.add(win);

      edifGroup.add(cGroup);
    }});

    // =========================================================================
    // 9. RÉGUAS E MALHAS DE ESCALA 1:1 (COMPROVAÇÃO 1m H = 1m V)
    // =========================================================================
    const scale1to1Rulers = [];

    function create1to1ScaleFrame(widthM, heightM, title, colorHex) {{
      const group = new THREE.Group();
      const lineMat = new THREE.LineBasicMaterial({{ color: colorHex, linewidth: 2 }});
      const gridMat = new THREE.LineBasicMaterial({{ color: colorHex, transparent: true, opacity: 0.45 }});

      // Borda Externa
      const borderPts = [
        new THREE.Vector3(-widthM / 2, 0, 0), new THREE.Vector3(widthM / 2, 0, 0),
        new THREE.Vector3(widthM / 2, heightM, 0), new THREE.Vector3(-widthM / 2, heightM, 0),
        new THREE.Vector3(-widthM / 2, 0, 0)
      ];
      const borderGeom = new THREE.BufferGeometry().setFromPoints(borderPts);
      group.add(new THREE.Line(borderGeom, lineMat));

      // Linhas verticais a cada 1,00 metro
      const gridPts = [];
      for (let x = -widthM / 2 + 1; x < widthM / 2; x += 1) {{
        gridPts.push(new THREE.Vector3(x, 0, 0), new THREE.Vector3(x, heightM, 0));
      }}
      // Linhas horizontais a cada 1,00 metro
      for (let y = 1; y < heightM; y += 1) {{
        gridPts.push(new THREE.Vector3(-widthM / 2, y, 0), new THREE.Vector3(widthM / 2, y, 0));
      }}
      const gridGeom = new THREE.BufferGeometry().setFromPoints(gridPts);
      group.add(new THREE.LineSegments(gridGeom, gridMat));
      return group;
    }}

    // Régua 1:1 na Casa do Sítio (14m x 4,65m)
    const casaScaleRuler = create1to1ScaleFrame(14.0, 4.65, 'CASA 1:1', 0xf59e0b);
    casaScaleRuler.position.set(0, 0.05, 6.2);
    casaGroup.add(casaScaleRuler);
    scale1to1Rulers.push(casaScaleRuler);

    // Régua 1:1 no Salão (12m x 5,2m)
    const salaoScaleRuler = create1to1ScaleFrame(12.0, 5.2, 'SALÃO 1:1', 0x38bdf8);
    salaoScaleRuler.position.set(0, 0.12, 4.25);
    salaoGroup.add(salaoScaleRuler);
    scale1to1Rulers.push(salaoScaleRuler);

    // Régua 1:1 na Quadra de Areia (22m x 6m)
    const quadraScaleRuler = create1to1ScaleFrame(22.0, 6.0, 'QUADRA 1:1', 0x10b981);
    quadraScaleRuler.position.set(0, 0.20, 6.25);
    quadraGroup.add(quadraScaleRuler);
    scale1to1Rulers.push(quadraScaleRuler);

    // =========================================================================
    // 10. INTERAÇÃO, CONTROLES DE ESCALA Z E NAVEGAÇÃO 3D
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

      // Ajusta posição vertical das edificações conforme escala Z
      casaGroup.position.y = casaData.base_y * currentZScale;
      salaoGroup.position.y = salaoData.base_y * currentZScale;
      quadraGroup.position.y = quadraData.base_y * currentZScale;
    }};

    window.setZScalePreset = function(val) {{
      document.getElementById('sliderZScale').value = val;
      setZScale(val);
    }};

    window.setSalaoOption = function(opt) {{
      optGroup1.visible = (opt === 1);
      optGroup2.visible = (opt === 2);
      optGroup3.visible = (opt === 3);

      const isNight = (opt === 4);
      floodlights.forEach(fl => {{ fl.intensity = isNight ? 2.5 : 0.0; }});
      if (isNight) {{
        optGroup1.visible = true; // Mantém a estrutura com refletores acesos
        scene.background = new THREE.Color(0x020617);
        hemiLight.intensity = 0.2;
        sunLight.intensity = 0.15;
      }} else {{
        scene.background = new THREE.Color(0x090d16);
        hemiLight.intensity = 0.85;
        sunLight.intensity = 1.35;
      }}

      for (let i = 1; i <= 4; i++) {{
        const b = document.getElementById('btnOpt' + i);
        if (b) b.classList.toggle('active', i === opt);
      }}
    }};

    window.goToView = function(view) {{
      let tCam, tTarget;
      if (view === 'casa') {{
        tCam = new THREE.Vector3(casaData.lx + 24, casaData.base_y + 14, casaData.lz + 26);
        tTarget = new THREE.Vector3(casaData.lx, casaData.base_y + 2.5, casaData.lz);
      }} else if (view === 'salao') {{
        tCam = new THREE.Vector3(salaoData.lx + 22, salaoData.base_y + 10, salaoData.lz + 18);
        tTarget = new THREE.Vector3(salaoData.lx, salaoData.base_y + 2.5, salaoData.lz);
      }} else if (view === 'quadra') {{
        tCam = new THREE.Vector3(quadraData.lx + 25, quadraData.base_y + 14, quadraData.lz + 22);
        tTarget = new THREE.Vector3(quadraData.lx, quadraData.base_y + 2.0, quadraData.lz);
      }} else if (view === 'chales') {{
        tCam = new THREE.Vector3(salaoData.lx + 38, salaoData.base_y + 26, salaoData.lz - 45);
        tTarget = new THREE.Vector3(salaoData.lx + 5, salaoData.base_y + 2.0, salaoData.lz - 25);
      }} else if (view === 'panoramica') {{
        tCam = new THREE.Vector3(0, casaData.base_y + 90, 115);
        tTarget = new THREE.Vector3(salaoData.lx * 0.5, salaoData.base_y, 0);
      }} else if (view === 'pedestre') {{
        tCam = new THREE.Vector3(casaData.lx + 10, casaData.base_y + 1.70, casaData.lz + 12);
        tTarget = new THREE.Vector3(casaData.lx, casaData.base_y + 2.0, casaData.lz);
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

    window.toggleEdif = function(show) {{ edifGroup.visible = show; }};
    window.toggleWire = function(show) {{ wireMesh.visible = show; }};
    window.toggleRulers = function(show) {{ scale1to1Rulers.forEach(r => {{ r.visible = show; }}); }};

    // Ferramenta Trena 3D
    let measureMode = false;
    let measurePoints = [];
    const measureLine = new THREE.Line(
      new THREE.BufferGeometry(),
      new THREE.LineBasicMaterial({{ color: 0xef4444, linewidth: 3 }})
    );
    scene.add(measureLine);

    window.toggleMeasureTool = function(active) {{
      measureMode = active;
      document.getElementById('measurer-box').style.display = active ? 'block' : 'none';
      measurePoints = [];
      measureLine.geometry.setFromPoints([]);
      document.getElementById('meas-result').innerText = 'Aguardando cliques...';
    }};

    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    window.addEventListener('click', (e) => {{
      if (!measureMode) return;
      if (e.target.closest('#panel')) return;

      mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
      raycaster.setFromCamera(mouse, camera);

      const hits = raycaster.intersectObjects([terrainMesh, edifGroup], true);
      if (hits.length > 0) {{
        const pt = hits[0].point;
        measurePoints.push(pt);
        if (measurePoints.length > 2) measurePoints = [pt];

        if (measurePoints.length === 1) {{
          document.getElementById('meas-result').innerText = `Ponto 1: E ${{ (CX_UTM + pt.x).toFixed(2) }}, N ${{ (CY_UTM - pt.z).toFixed(2) }}, Cota ${{ (Z_MIN + pt.y).toFixed(2) }}m`;
          measureLine.geometry.setFromPoints([]);
        }} else if (measurePoints.length === 2) {{
          const p1 = measurePoints[0];
          const p2 = measurePoints[1];
          measureLine.geometry.setFromPoints([p1, p2]);
          const dH = Math.hypot(p2.x - p1.x, p2.z - p1.z);
          const dV = Math.abs(p2.y - p1.y);
          const dTotal = p1.distanceTo(p2);
          document.getElementById('meas-result').innerHTML = `
            Distância Total: <b>${{dTotal.toFixed(2)}} m</b><br>
            Horizontal (H): <b>${{dH.toFixed(2)}} m</b> | Vertical (V): <b>${{dV.toFixed(2)}} m</b>
          `;
        }}
      }}
    }});

    // Loop de Animação
    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}
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

    print(f"\n6. Gravando arquivo HTML: {HTML_OUT}")
    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html_code)

    file_size_kb = os.path.getsize(HTML_OUT) / 1024
    print(f"   Sucesso! Arquivo gerado com {file_size_kb:.1f} KB.")
    print("=" * 80)


if __name__ == "__main__":
    main()
