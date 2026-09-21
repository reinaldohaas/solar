#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Processa e prolonga o MDT do SIGSC para cobrir toda a área de voo do drone (168 ha).
Renderiza com a Ortofoto Oficial SIGSC 0,39m perfeitamente casada com o relevo (100% nativo)
e sem linhas de voo do drone no visualizador 3D.
"""

import os
import io
import json
import base64
import zipfile
import xml.etree.ElementTree as ET
import rasterio
from rasterio.windows import from_bounds
import numpy as np
from PIL import Image, ImageEnhance
from pyproj import Transformer
import geopandas as gpd

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"

MDT_SOURCE = os.path.join(SIGSC_DIR, "raster", "mdt_sigsc", "MDT_SG-22-Z-D-I-3-SE-A.tif")
ORTO_SIGSC_SOURCE = os.path.join(SIGSC_DIR, "raster", "ortofoto_sigsc", "Orto-RGB_SG-22-Z-D-I-3-SE-A.tif")
KMZ_DRONE_2024 = os.path.join(SOLAR_DIR, "Estrada-Ribeiro-dos-Ovos-01-06-2024-orthophoto_1.kmz")
KMZ_DRONE_2026 = os.path.join(SOLAR_DIR, "Estrada-Ribeiro-dos-Ovos-01-03-2026-orthophoto.kmz")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")

# Bounding box estendido cobrindo toda a extensão do voo do drone e da estrada (SIRGAS 2000 UTM 22S)
LEFT = 662900.0
BOTTOM = 6967950.0
RIGHT = 664150.0
TOP = 6969300.0
WIDTH_M = RIGHT - LEFT   # 1250 m
DEPTH_M = TOP - BOTTOM   # 1350 m
CX = (LEFT + RIGHT) / 2.0
CY = (BOTTOM + TOP) / 2.0

RES = 0.5  # 0.5 m por pixel
W_PX = int(round(WIDTH_M / RES))  # 2500 px
H_PX = int(round(DEPTH_M / RES))  # 2700 px

OUT_MDT = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Estendida.tif")
OUT_ORTO_SIGSC = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Area_Estendida.tif")
OUT_ORTO_COMP = os.path.join(SOLAR_DIR, "Ortofoto_Drone_Composicao_Estendida.tif")
OUT_ORTO_PURA = os.path.join(SOLAR_DIR, "Ortofoto_Drone_Pura_Estendida.tif")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")

def extract_extended_mdt():
    print("1. Extraindo MDT estendido do SIGSC para a área do drone...")
    with rasterio.open(MDT_SOURCE) as src:
        win = from_bounds(LEFT, BOTTOM, RIGHT, TOP, src.transform)
        elev = src.read(1, window=win)
        win_transform = rasterio.windows.transform(win, src.transform)
        meta = src.meta.copy()
        meta.update({
            'height': elev.shape[0],
            'width': elev.shape[1],
            'transform': win_transform,
            'compress': 'deflate'
        })
        with rasterio.open(OUT_MDT, 'w', **meta) as dst:
            dst.write(elev, 1)
    print(f"   MDT Estendido salvo: {OUT_MDT} ({elev.shape[1]}x{elev.shape[0]} px, 1.0m)")
    return elev

def extract_sigsc_ortho_base():
    print("2. Extraindo Ortofoto Oficial SIGSC (0,39m) ortorretificada no MDT...")
    with rasterio.open(ORTO_SIGSC_SOURCE) as src:
        win = from_bounds(LEFT, BOTTOM, RIGHT, TOP, src.transform)
        rgb = src.read((1, 2, 3), window=win)
        win_trans = rasterio.windows.transform(win, src.transform)
        meta = src.meta.copy()
        meta.update({
            'height': rgb.shape[1],
            'width': rgb.shape[2],
            'transform': win_trans,
            'compress': 'deflate'
        })
        with rasterio.open(OUT_ORTO_SIGSC, 'w', **meta) as dst:
            dst.write(rgb)

    im = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    im_resized = im.resize((W_PX, H_PX), Image.Resampling.LANCZOS)
    return im_resized.convert("RGBA")

def stamp_tiles(canvas, kmz_path, level_prefix, to_utm):
    print(f"   Processando tiles de {os.path.basename(kmz_path)} (nível {level_prefix})...")
    with zipfile.ZipFile(kmz_path, 'r') as z:
        tiles = []
        for fn in z.namelist():
            if fn.startswith(level_prefix) and fn.endswith('.kml'):
                png_fn = fn[:-4] + '.png'
                if png_fn in z.namelist():
                    root = ET.fromstring(z.read(fn))
                    box = root.find('.//{http://www.opengis.net/kml/2.2}LatLonBox') or root.find('.//{http://www.opengis.net/kml/2.2}LatLonAltBox')
                    n = float(box.find('{http://www.opengis.net/kml/2.2}north').text)
                    s = float(box.find('{http://www.opengis.net/kml/2.2}south').text)
                    e = float(box.find('{http://www.opengis.net/kml/2.2}east').text)
                    w = float(box.find('{http://www.opengis.net/kml/2.2}west').text)
                    tiles.append((png_fn, n, s, e, w))

        count = 0
        for png_fn, n, s, e, w in tiles:
            x0, y1 = to_utm.transform(w, n)
            x1, y0 = to_utm.transform(e, s)
            px0 = int(round((x0 - LEFT) / RES))
            px1 = int(round((x1 - LEFT) / RES))
            py0 = int(round((TOP - y1) / RES))
            py1 = int(round((TOP - y0) / RES))

            pw = px1 - px0
            ph = py1 - py0
            if pw <= 0 or ph <= 0:
                continue

            try:
                tile_im = Image.open(io.BytesIO(z.read(png_fn))).convert("RGBA")
                tile_resized = tile_im.resize((pw, ph), Image.Resampling.BILINEAR)
                canvas.alpha_composite(tile_resized, (px0, py0))
                count += 1
            except Exception:
                pass
        print(f"   {count} tiles estampados.")

def save_geotiff(pil_img, out_path):
    print(f"Salvando GeoTIFF: {out_path}...")
    from rasterio.transform import from_bounds
    transform = from_bounds(LEFT, BOTTOM, RIGHT, TOP, W_PX, H_PX)
    arr = np.array(pil_img)
    bands = arr.shape[2]
    meta = {
        'driver': 'GTiff',
        'dtype': 'uint8',
        'nodata': 0 if bands == 4 else None,
        'width': W_PX,
        'height': H_PX,
        'count': bands,
        'crs': 'EPSG:31982',
        'transform': transform,
        'compress': 'deflate'
    }
    with rasterio.open(out_path, 'w', **meta) as dst:
        for b in range(bands):
            dst.write(arr[:, :, b], b + 1)
    print(f"   Salvo: {out_path}")

def build_visualizer_html(elev, img_drone_comp, img_sigsc_base):
    print("4. Montando Visualizador 3D com a Ortofoto Oficial SIGSC no MDT e sem linhas de voo...")
    step = 5
    elev_sub = elev[::step, ::step]
    rows, cols = elev_sub.shape

    z_min = float(np.min(elev_sub))
    z_max = float(np.max(elev_sub))
    elev_clean = np.where(np.isnan(elev_sub), z_min, elev_sub)
    heights_list = elev_clean.tolist()

    tex_w = 2048
    tex_h = int(round(tex_w * (DEPTH_M / WIDTH_M)))

    # 1. Ortofoto SIGSC Oficial (0,39m) em Base64 - TEXTURA PADRÃO E PRINCIPAL
    s_rgb = img_sigsc_base.convert("RGB").resize((tex_w, tex_h), Image.Resampling.LANCZOS)
    enhancer_s = ImageEnhance.Contrast(s_rgb)
    s_rgb = enhancer_s.enhance(1.18)
    bright_s = ImageEnhance.Brightness(s_rgb)
    s_rgb = bright_s.enhance(1.08)
    buf_sigsc = io.BytesIO()
    s_rgb.save(buf_sigsc, format='JPEG', quality=88)
    b64_sigsc = base64.b64encode(buf_sigsc.getvalue()).decode('utf-8')
    print(f"   Ortofoto Oficial SIGSC Base64 gerada (~{round(len(b64_sigsc)/1024)} KB)")

    # 2. Ortofoto Drone Base64 (para alternância opcional)
    d_rgb = img_drone_comp.convert("RGB").resize((tex_w, tex_h), Image.Resampling.LANCZOS)
    enhancer_d = ImageEnhance.Contrast(d_rgb)
    d_rgb = enhancer_d.enhance(1.15)
    buf_drone = io.BytesIO()
    d_rgb.save(buf_drone, format='JPEG', quality=86)
    b64_drone = base64.b64encode(buf_drone.getvalue()).decode('utf-8')

    # Vetores GPKG
    tables_data = []
    for setor in ['p1', 'p2', 'p3']:
        gdf = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor}')
        for _, r in gdf.iterrows():
            c = r.geometry.centroid
            tables_data.append({
                'setor': setor.upper(),
                'id': int(r['mesa_id']),
                'x': round(c.x - CX, 2),
                'y': round(r['cota_painel_inferior_m'] - z_min, 2),
                'z': round(-(c.y - CY), 2),
                'cota': float(r['cota_terreno_m'])
            })

    gdf_salao = gpd.read_file(GPKG_PATH, layer='edificacao_salao').iloc[0]
    sc = gdf_salao.geometry.centroid
    salao_data = {
        'x': round(sc.x - CX, 2),
        'y': round(gdf_salao['cota_piso_m'] - z_min, 2),
        'z': round(-(sc.y - CY), 2),
        'cota': float(gdf_salao['cota_piso_m'])
    }

    gdf_campo = gpd.read_file(GPKG_PATH, layer='campo_de_areia').iloc[0]
    cc = gdf_campo.geometry.centroid
    campo_data = {
        'x': round(cc.x - CX, 2),
        'y': round(gdf_campo['cota_areia_m'] - z_min, 2),
        'z': round(-(cc.y - CY), 2),
        'cota': float(gdf_campo['cota_areia_m'])
    }

    # Limite da propriedade Sítio das Andorinhas (18,60 ha)
    gdf_limite = gpd.read_file(GPKG_PATH, layer='limite_sitio').iloc[0]
    limite_coords = []
    for x, y in gdf_limite.geometry.exterior.coords:
        col_idx = int(round((x - LEFT) / WIDTH_M * (cols - 1)))
        row_idx = int(round((TOP - y) / DEPTH_M * (rows - 1)))
        col_idx = max(0, min(cols - 1, col_idx))
        row_idx = max(0, min(rows - 1, row_idx))
        h = float(elev_clean[row_idx, col_idx]) - z_min + 1.5
        limite_coords.append({'x': round(x - CX, 2), 'y': round(h, 2), 'z': round(-(y - CY), 2)})

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D — Sítio das Andorinhas (MDT & Ortofoto Nativo SIGSC)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #0b111e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    #canvas-container {{ width: 100vw; height: 100vh; }}
    
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 360px;
      background: rgba(15, 23, 42, 0.90); color: #f8fafc; padding: 20px;
      border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(12px);
      z-index: 10; max-height: calc(100vh - 32px); overflow-y: auto;
    }}
    h1 {{ font-size: 16px; font-weight: 700; margin-bottom: 2px; color: #38bdf8; }}
    .badge {{ display: inline-block; font-size: 10.5px; font-weight: 600; padding: 3px 8px; border-radius: 4px; background: #0284c7; color: #fff; margin-bottom: 12px; }}
    .stat-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 4.5px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }}
    .stat-lbl {{ color: #94a3b8; }}
    .stat-val {{ font-weight: 600; color: #4ade80; }}
    .stat-highlight {{ color: #fbbf24; font-weight: 700; }}
    
    .btn-group {{ margin-top: 14px; display: flex; flex-direction: column; gap: 6px; }}
    .btn {{
      background: #0284c7; border: none; color: white; padding: 8px 12px;
      border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600;
      transition: all 0.2s; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px;
    }}
    .btn:hover {{ background: #0369a1; transform: translateY(-1px); }}
    .btn-secondary {{ background: #1e293b; border: 1px solid #334155; color: #e2e8f0; }}
    .btn-secondary:hover {{ background: #334155; }}
    .btn-accent {{ background: #059669; }}
    .btn-accent:hover {{ background: #047857; }}
    .btn-toggle {{ background: #d97706; }}
    .btn-toggle:hover {{ background: #b45309; }}
    
    #instructions {{
      position: absolute; bottom: 16px; left: 16px; background: rgba(15, 23, 42, 0.85);
      color: #94a3b8; padding: 8px 14px; border-radius: 8px; font-size: 11px;
      border: 1px solid rgba(255,255,255,0.08); backdrop-filter: blur(8px);
    }}
    #loading {{
      position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
      background: rgba(15, 23, 42, 0.95); color: #38bdf8; padding: 24px 36px;
      border-radius: 12px; font-size: 16px; font-weight: 600; border: 1px solid rgba(255,255,255,0.15);
      box-shadow: 0 10px 40px rgba(0,0,0,0.6); text-align: center;
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
  <div id="loading"><div class="spinner"></div>Carregando Modelo 3D Nativo SIGSC...</div>
  <div id="canvas-container"></div>
  
  <div id="panel">
    <h1>SÍTIO DAS ANDORINHAS 3D</h1>
    <div class="badge">MDT 1,0 m + Ortofoto Oficial SIGSC (168,75 ha)</div>
    
    <div class="stat-row"><span class="stat-lbl">Área do Terreno 3D:</span><span class="stat-val">168,75 ha (1.250×1.350 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">Área do Sítio:</span><span class="stat-val">18,60 ha (amarelo)</span></div>
    <div class="stat-row"><span class="stat-lbl">Cota Mínima / Máxima:</span><span class="stat-val">{z_min:.1f} m / {z_max:.1f} m</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P1 (Otimizado):</span><span class="stat-val">114 mesas (925,7 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P2:</span><span class="stat-val">73 mesas (592,8 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P3:</span><span class="stat-val">46 mesas (373,5 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Salão Telhado Reto:</span><span class="stat-val">18 módulos (10,4 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Campo de Areia e Redes:</span><span class="stat-val">22 × 12 m (h=6 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">POTÊNCIA TOTAL USINA:</span><span class="stat-val stat-highlight">1.902,4 kWp (~1,90 MWp)</span></div>

    <div class="btn-group">
      <button class="btn btn-toggle" id="btn-texture" onclick="toggleTexture()">📷 Alternar para Foto do Drone</button>
      <button class="btn btn-secondary" onclick="focusOn('p1')">🔎 Focar no Setor P1 (114 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p2')">🔎 Focar no Setor P2 (73 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3 (46 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Estendida</button>
      <button class="btn btn-secondary" onclick="toggleBoundary()">🟡 Exibir/Ocultar Limite do Sítio</button>
      <button class="btn btn-accent" onclick="toggleWireframe()">⚡ Alternar Relevo Wireframe</button>
    </div>
  </div>

  <div id="instructions">
    🖱️ <b>Mouse:</b> Botão esquerdo para girar | Botão direito para transladar | Roda para zoom
  </div>

  <script>
    const widthM = {WIDTH_M:.2f};
    const depthM = {DEPTH_M:.2f};
    const rows = {rows};
    const cols = {cols};
    const heights = {json.dumps(heights_list)};
    const zMin = {z_min:.2f};
    const tables = {json.dumps(tables_data)};
    const salao = {json.dumps(salao_data)};
    const campo = {json.dumps(campo_data)};
    const limiteCoords = {json.dumps(limite_coords)};

    const texSigscBase64 = "data:image/jpeg;base64,{b64_sigsc}";
    const texDroneBase64 = "data:image/jpeg;base64,{b64_drone}";

    // Setup Three.js
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xdce7ef);
    scene.fog = new THREE.FogExp2(0xdce7ef, 0.0003);

    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 2, 10000);
    camera.position.set(-200, 650, 750);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: 'high-performance' }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputEncoding = THREE.sRGBEncoding;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.target.set(0, 50, 0);

    // Luzes diurnas naturais
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x64748b, 0.85);
    hemiLight.position.set(0, 800, 0);
    scene.add(hemiLight);

    const sun = new THREE.DirectionalLight(0xfff8ee, 1.25);
    sun.position.set(-450, 1100, -350);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.left = -900;
    sun.shadow.camera.right = 900;
    sun.shadow.camera.top = 900;
    sun.shadow.camera.bottom = -900;
    scene.add(sun);

    const fillLight = new THREE.DirectionalLight(0xa5b4fc, 0.45);
    fillLight.position.set(500, 600, 600);
    scene.add(fillLight);

    // 1. Geometria do Terreno Estendido (MDT SIGSC 168 ha)
    const geom = new THREE.PlaneGeometry(widthM, depthM, cols - 1, rows - 1);
    geom.rotateX(-Math.PI / 2);

    const pos = geom.attributes.position;
    for (let r = 0; r < rows; r++) {{
      for (let c = 0; c < cols; c++) {{
        const idx = r * cols + c;
        const h = heights[r][c] - zMin;
        pos.setY(idx, h);
      }}
    }}
    geom.computeVertexNormals();

    // 2. Texturas: SIGSC Oficial (PADRÃO 100% ORTORRETIFICADO NO MDT) e Drone
    const texSigsc = new THREE.Texture();
    const imgSigsc = new Image();
    imgSigsc.onload = function() {{
      texSigsc.image = imgSigsc;
      texSigsc.encoding = THREE.sRGBEncoding;
      if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
        texSigsc.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }}
      texSigsc.needsUpdate = true;
      document.getElementById('loading').style.display = 'none';
      renderer.render(scene, camera);
    }};
    imgSigsc.src = texSigscBase64;
    if (imgSigsc.complete) {{ imgSigsc.onload(); }}

    const texDrone = new THREE.Texture();
    const imgDrone = new Image();
    imgDrone.onload = function() {{
      texDrone.image = imgDrone;
      texDrone.encoding = THREE.sRGBEncoding;
      texDrone.needsUpdate = true;
    }};
    imgDrone.src = texDroneBase64;

    // O Terreno inicia com a Ortofoto Oficial SIGSC (ortorretificada no MDT)
    const matTerrain = new THREE.MeshStandardMaterial({{
      color: 0xffffff,
      map: texSigsc,
      roughness: 0.85,
      metalness: 0.05,
      side: THREE.DoubleSide
    }});
    const terrain = new THREE.Mesh(geom, matTerrain);
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 3. Limite do Sítio das Andorinhas (18,60 ha em amarelo)
    const boundaryPoints = [];
    limiteCoords.forEach(p => {{
      boundaryPoints.push(new THREE.Vector3(p.x, p.y, p.z));
    }});
    const boundaryGeom = new THREE.BufferGeometry().setFromPoints(boundaryPoints);
    const boundaryMat = new THREE.LineBasicMaterial({{ color: 0xffea00, linewidth: 2.5 }});
    const boundaryLine = new THREE.Line(boundaryGeom, boundaryMat);
    scene.add(boundaryLine);

    // 4. Mesas Solares Solo (P1, P2, P3)
    const solarGroup = new THREE.Group();
    const tableGeom = new THREE.BoxGeometry(8.0, 0.22, 4.32);
    tableGeom.rotateX(THREE.MathUtils.degToRad(20));

    const moduleMat = new THREE.MeshStandardMaterial({{ color: 0x1d4ed8, metalness: 0.8, roughness: 0.2 }});
    const postMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.6, roughness: 0.4 }});
    const postGeom = new THREE.CylinderGeometry(0.08, 0.08, 1.6, 6);

    tables.forEach(t => {{
      const mesaMesh = new THREE.Mesh(tableGeom, moduleMat);
      mesaMesh.position.set(t.x, t.y + 1.25, t.z);
      mesaMesh.castShadow = true;
      solarGroup.add(mesaMesh);

      const postFront = new THREE.Mesh(postGeom, postMat);
      postFront.position.set(t.x - 2.5, t.y + 0.6, t.z + 1.4);
      solarGroup.add(postFront);

      const postBack = new THREE.Mesh(postGeom, postMat);
      postBack.position.set(t.x + 2.5, t.y + 1.0, t.z - 1.4);
      solarGroup.add(postBack);
    }});
    scene.add(solarGroup);

    // 5. Salão de Eventos (Telhado Reto com Usina Solar)
    const salaoGroup = new THREE.Group();
    const salaoBody = new THREE.Mesh(
      new THREE.BoxGeometry(11.0, 3.5, 8.11),
      new THREE.MeshStandardMaterial({{ color: 0xf1f5f9, roughness: 0.7 }})
    );
    salaoBody.position.set(salao.x, salao.y + 1.75, salao.z);
    salaoBody.castShadow = true;
    salaoBody.receiveShadow = true;
    salaoGroup.add(salaoBody);

    const platibanda = new THREE.Mesh(
      new THREE.BoxGeometry(11.2, 0.4, 8.3),
      new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.5 }})
    );
    platibanda.position.set(salao.x, salao.y + 3.7, salao.z);
    salaoGroup.add(platibanda);

    const roofModuleGeom = new THREE.BoxGeometry(1.15, 0.08, 2.38);
    roofModuleGeom.rotateX(THREE.MathUtils.degToRad(18));
    for (let row = 0; row < 2; row++) {{
      for (let col = 0; col < 9; col++) {{
        const rm = new THREE.Mesh(roofModuleGeom, moduleMat);
        rm.position.set(salao.x - 4.8 + col * 1.2, salao.y + 4.15, salao.z - 1.6 + row * 3.2);
        salaoGroup.add(rm);
      }}
    }}
    scene.add(salaoGroup);

    // 6. Campo de Areia e Redes de Proteção 3D
    const campoGroup = new THREE.Group();
    const sandMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 0.18, 12.0),
      new THREE.MeshStandardMaterial({{ color: 0xfde047, roughness: 0.95 }})
    );
    sandMesh.position.set(campo.x, campo.y + 0.1, campo.z);
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    const netMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 6.0, 12.0),
      new THREE.MeshBasicMaterial({{ color: 0x334155, wireframe: true, transparent: true, opacity: 0.4 }})
    );
    netMesh.position.set(campo.x, campo.y + 3.0, campo.z);
    campoGroup.add(netMesh);
    scene.add(campoGroup);

    // Alternar Texturas (SIGSC Oficial <-> Drone)
    let currentTexture = 'sigsc';
    function toggleTexture() {{
      if (currentTexture === 'sigsc') {{
        matTerrain.map = texDrone;
        currentTexture = 'drone';
        document.getElementById('btn-texture').innerText = '📷 Alternar para Foto Oficial SIGSC';
      }} else {{
        matTerrain.map = texSigsc;
        currentTexture = 'sigsc';
        document.getElementById('btn-texture').innerText = '📷 Alternar para Foto do Drone';
      }}
      matTerrain.needsUpdate = true;
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
        controls.target.set(salao.x, salao.y, salao.z);
        camera.position.set(salao.x - 50, salao.y + 35, salao.z + 75);
      }} else {{
        controls.target.set(0, 40, 0);
        camera.position.set(-200, 650, 750);
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
      boundaryLine.visible = showBoundary;
    }}

    window.addEventListener('resize', () => {{
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    }});

    function animate() {{
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }}
    animate();
  </script>
</body>
</html>"""

    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Visualizador 3D com MDT e Ortofoto SIGSC gerado com sucesso: {HTML_OUT}")

def main():
    elev = extract_extended_mdt()
    img_sigsc_base = extract_sigsc_ortho_base()

    to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:31982', always_xy=True)

    print("3. Gerando mosaico da Ortofoto do Drone...")
    canvas_comp = img_sigsc_base.copy()
    canvas_pura = Image.new("RGBA", (W_PX, H_PX), (0, 0, 0, 0))

    if os.path.exists(KMZ_DRONE_2024):
        stamp_tiles(canvas_comp, KMZ_DRONE_2024, '6/', to_utm)
        stamp_tiles(canvas_pura, KMZ_DRONE_2024, '6/', to_utm)

    if os.path.exists(KMZ_DRONE_2026):
        stamp_tiles(canvas_comp, KMZ_DRONE_2026, '4/', to_utm)
        stamp_tiles(canvas_pura, KMZ_DRONE_2026, '4/', to_utm)

    save_geotiff(canvas_comp.convert("RGB"), OUT_ORTO_COMP)
    save_geotiff(canvas_pura, OUT_ORTO_PURA)

    build_visualizer_html(elev, canvas_comp, img_sigsc_base)
    print("Processamento concluído com êxito!")

if __name__ == '__main__':
    main()
