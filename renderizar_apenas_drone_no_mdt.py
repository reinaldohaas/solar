#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o modelo 3D com a Ortofoto Pura do Drone (odm_orthophoto.tif) no topo do MDT do SIGSC,
removendo completamente qualquer imagem de Estrada-Ribeiro-dos-Ovos-01-03-2026-orthophoto.kmz,
sem sobreposição de imagens do SIGSC por cima do drone, e sem linhas de voo.
"""

import os
import io
import json
import base64
import rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
import numpy as np
from PIL import Image, ImageEnhance
import geopandas as gpd

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"

DRONE_TIF = r"C:\Users\haas\OneDrive\Documentos\sitio_andorinhas\Estrada-Ribeiro-dos-Ovos-01-06-2024-all\odm_orthophoto\odm_orthophoto.tif"
MDT_SOURCE = os.path.join(SIGSC_DIR, "raster", "mdt_sigsc", "MDT_SG-22-Z-D-I-3-SE-A.tif")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")

OUT_MDT = os.path.join(SOLAR_DIR, "MDT_SIGSC_Area_Drone_Exata.tif")
OUT_DRONE_TIF = os.path.join(SOLAR_DIR, "Ortofoto_Drone_Nativa_Exata.tif")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")

def main():
    print("1. Abrindo Ortofoto Nativa do Drone (WebODM GeoTIFF)...")
    with rasterio.open(DRONE_TIF) as src_drone:
        db = src_drone.bounds
        drone_w = src_drone.width
        drone_h = src_drone.height
        
        # Limites exatos do voo do drone
        left = float(db.left)
        bottom = float(db.bottom)
        right = float(db.right)
        top = float(db.top)
        width_m = right - left
        depth_m = top - bottom
        cx = (left + right) / 2.0
        cy = (bottom + top) / 2.0
        
        print(f"   Limites do Drone: X=[{left:.2f}, {right:.2f}], Y=[{bottom:.2f}, {top:.2f}]")
        print(f"   Dimensões: {width_m:.1f} m x {depth_m:.1f} m")

        # Ler ortofoto em alta definição para o visualizador (2048 x 2414 px)
        tex_w = 2048
        tex_h = int(round(tex_w * drone_h / drone_w))
        print(f"   Lendo e otimizando imagem do drone em {tex_w}x{tex_h} px...")
        rgba = src_drone.read(
            out_shape=(src_drone.count, tex_h, tex_w),
            resampling=Resampling.bilinear
        )

    # Converter para RGB
    rgb = np.transpose(rgba[:3], (1, 2, 0))
    if rgba.shape[0] == 4:
        alpha = rgba[3]
        mask = (alpha < 30)
        rgb[mask] = [38, 50, 32] # Verde natural discreto de borda

    img_drone = Image.fromarray(rgb)
    enhancer = ImageEnhance.Contrast(img_drone)
    img_drone = enhancer.enhance(1.16)
    bright = ImageEnhance.Brightness(img_drone)
    img_drone = bright.enhance(1.08)

    buf = io.BytesIO()
    img_drone.save(buf, format='JPEG', quality=88)
    b64_drone = base64.b64encode(buf.getvalue()).decode('utf-8')
    print(f"   Ortofoto do Drone codificada em Base64 (~{round(len(b64_drone)/1024)} KB)")

    # 2. Extrair MDT do SIGSC correspondente EXATAMENTE aos limites do drone
    print("2. Recortando MDT do SIGSC exatamente nos limites da ortofoto do drone...")
    with rasterio.open(MDT_SOURCE) as src_mdt:
        win = from_bounds(left, bottom, right, top, src_mdt.transform)
        elev = src_mdt.read(1, window=win)
        win_transform = rasterio.windows.transform(win, src_mdt.transform)
        meta = src_mdt.meta.copy()
        meta.update({
            'height': elev.shape[0],
            'width': elev.shape[1],
            'transform': win_transform,
            'compress': 'deflate'
        })
        with rasterio.open(OUT_MDT, 'w', **meta) as dst:
            dst.write(elev, 1)

    print(f"   MDT Exato salvo: {OUT_MDT} ({elev.shape[1]}x{elev.shape[0]} px, 1.0m)")
    print(f"   Cota Mínima: {elev.min():.1f} m | Cota Máxima: {elev.max():.1f} m")

    # 3. Subamostragem para a malha 3D do Three.js
    step = 5
    elev_sub = elev[::step, ::step]
    rows, cols = elev_sub.shape
    z_min = float(np.min(elev_sub))
    z_max = float(np.max(elev_sub))
    elev_clean = np.where(np.isnan(elev_sub), z_min, elev_sub)
    heights_list = elev_clean.tolist()

    # 4. Vetores GPKG ajustados para o centro da cena
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
        'z': round(-(sc.y - cy), 2),
        'cota': float(gdf_salao['cota_piso_m'])
    }

    gdf_campo = gpd.read_file(GPKG_PATH, layer='campo_de_areia').iloc[0]
    cc = gdf_campo.geometry.centroid
    campo_data = {
        'x': round(cc.x - cx, 2),
        'y': round(gdf_campo['cota_areia_m'] - z_min, 2),
        'z': round(-(cc.y - cy), 2),
        'cota': float(gdf_campo['cota_areia_m'])
    }

    # Limite do Sítio das Andorinhas (18,60 ha)
    gdf_limite = gpd.read_file(GPKG_PATH, layer='limite_sitio').iloc[0]
    limite_coords = []
    for x, y in gdf_limite.geometry.exterior.coords:
        col_idx = int(round((x - left) / width_m * (cols - 1)))
        row_idx = int(round((top - y) / depth_m * (rows - 1)))
        col_idx = max(0, min(cols - 1, col_idx))
        row_idx = max(0, min(rows - 1, row_idx))
        h = float(elev_clean[row_idx, col_idx]) - z_min + 1.5
        limite_coords.append({'x': round(x - cx, 2), 'y': round(h, 2), 'z': round(-(y - cy), 2)})

    print("5. Montando Visualizador 3D com as Fotos de Drone Exclusivas no Relevo SIGSC...")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D — Sítio das Andorinhas (Fotos de Drone sobre Relevo SIGSC)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #0b111e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    #canvas-container {{ width: 100vw; height: 100vh; }}
    
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 360px;
      background: rgba(15, 23, 42, 0.92); color: #f8fafc; padding: 20px;
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
  <div id="loading"><div class="spinner"></div>Carregando Fotos de Drone no Relevo SIGSC...</div>
  <div id="canvas-container"></div>
  
  <div id="panel">
    <h1>SÍTIO DAS ANDORINHAS 3D</h1>
    <div class="badge">Ortofoto Pura do Drone (7,4 cm) sobre MDT SIGSC</div>
    
    <div class="stat-row"><span class="stat-lbl">Área de Voo do Drone:</span><span class="stat-val">{width_m:.0f} × {depth_m:.0f} m (137,8 ha)</span></div>
    <div class="stat-row"><span class="stat-lbl">Área do Sítio:</span><span class="stat-val">18,60 ha (linha amarela)</span></div>
    <div class="stat-row"><span class="stat-lbl">Cota Mínima / Máxima:</span><span class="stat-val">{z_min:.1f} m / {z_max:.1f} m</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P1 (Otimizado):</span><span class="stat-val">114 mesas (925,7 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P2:</span><span class="stat-val">73 mesas (592,8 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">UFV Solo P3:</span><span class="stat-val">46 mesas (373,5 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Salão Telhado Reto:</span><span class="stat-val">18 módulos (10,4 kWp)</span></div>
    <div class="stat-row"><span class="stat-lbl">Campo de Areia e Redes:</span><span class="stat-val">22 × 12 m (h=6 m)</span></div>
    <div class="stat-row"><span class="stat-lbl">POTÊNCIA TOTAL USINA:</span><span class="stat-val stat-highlight">1.902,4 kWp (~1,90 MWp)</span></div>

    <div class="btn-group">
      <button class="btn btn-secondary" onclick="focusOn('p1')">🔎 Focar no Setor P1 (114 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p2')">🔎 Focar no Setor P2 (73 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3 (46 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Geral</button>
      <button class="btn btn-secondary" onclick="toggleBoundary()">🟡 Exibir/Ocultar Limite do Sítio</button>
      <button class="btn btn-accent" onclick="toggleWireframe()">⚡ Alternar Relevo Wireframe</button>
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
    const heights = {json.dumps(heights_list)};
    const zMin = {z_min:.2f};
    const tables = {json.dumps(tables_data)};
    const salao = {json.dumps(salao_data)};
    const campo = {json.dumps(campo_data)};
    const limiteCoords = {json.dumps(limite_coords)};

    const texDroneBase64 = "data:image/jpeg;base64,{b64_drone}";

    // Setup Three.js
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xdce7ef);
    scene.fog = new THREE.FogExp2(0xdce7ef, 0.0003);

    const camera = new THREE.PerspectiveCamera(40, window.innerWidth / window.innerHeight, 2, 10000);
    camera.position.set(-180, 600, 700);

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
    controls.target.set(0, 45, 0);

    // Iluminação natural
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x64748b, 0.85);
    hemiLight.position.set(0, 800, 0);
    scene.add(hemiLight);

    const sun = new THREE.DirectionalLight(0xfff8ee, 1.25);
    sun.position.set(-450, 1100, -350);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.left = -800;
    sun.shadow.camera.right = 800;
    sun.shadow.camera.top = 800;
    sun.shadow.camera.bottom = -800;
    scene.add(sun);

    const fillLight = new THREE.DirectionalLight(0xa5b4fc, 0.45);
    fillLight.position.set(500, 600, 600);
    scene.add(fillLight);

    // 1. Geometria do Terreno MDT SIGSC (dimensões exatas do drone)
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

    // 2. Textura da Ortofoto Pura do Drone (NO TOPO, VISÍVEL EM 100% DO RELEVO)
    const texDrone = new THREE.Texture();
    const imgDrone = new Image();
    imgDrone.onload = function() {{
      texDrone.image = imgDrone;
      texDrone.encoding = THREE.sRGBEncoding;
      if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
        texDrone.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }}
      texDrone.needsUpdate = true;
      document.getElementById('loading').style.display = 'none';
      renderer.render(scene, camera);
    }};
    imgDrone.src = texDroneBase64;
    if (imgDrone.complete) {{ imgDrone.onload(); }}

    const matTerrain = new THREE.MeshStandardMaterial({{
      color: 0xffffff,
      map: texDrone,
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
    print(f"Visualizador 3D com Fotos de Drone Exclusivas gerado com sucesso: {HTML_OUT}")

if __name__ == '__main__':
    main()
