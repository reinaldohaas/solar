#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o Visualizador 3D Web Interativo do Sítio das Andorinhas em HTML/Three.js
100% nativo SIGSC, com a Ortofoto Oficial 0,39m embutida em Base64 (zero CORS).
"""

import os
import io
import json
import base64
import rasterio
from rasterio.windows import from_bounds
import numpy as np
from PIL import Image, ImageEnhance
import geopandas as gpd

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"
MDT_PATH = os.path.join(SOLAR_DIR, "MDT_Novo_sitio_das_andorinhas.tif")
SHEET_PATH = os.path.join(SIGSC_DIR, "raster", "ortofoto_sigsc", "Orto-RGB_SG-22-Z-D-I-3-SE-A.tif")
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")

def main():
    print("1. Lendo MDT do SIGSC...")
    with rasterio.open(MDT_PATH) as src:
        elev = src.read(1)
        bounds = src.bounds
        nodata = src.nodata

    # Subamostragem da grade do terreno (passo 4 = resolução de 4m)
    step = 4
    elev_sub = elev[::step, ::step]
    rows, cols = elev_sub.shape

    valid = elev_sub[(elev_sub != nodata) & (~np.isnan(elev_sub))]
    z_min = float(np.min(valid))
    z_max = float(np.max(valid))
    elev_clean = np.where((elev_sub == nodata) | (np.isnan(elev_sub)), z_min, elev_sub)

    width_m = bounds.right - bounds.left
    depth_m = bounds.top - bounds.bottom
    cx = (bounds.left + bounds.right) / 2.0
    cy = (bounds.bottom + bounds.top) / 2.0

    heights_list = elev_clean.tolist()

    print("2. Extraindo e otimizando Ortofoto Oficial SIGSC (0,39m)...")
    with rasterio.open(SHEET_PATH) as sheet:
        win = from_bounds(bounds.left, bounds.bottom, bounds.right, bounds.top, sheet.transform)
        rgb = sheet.read((1, 2, 3), window=win)

    # Redimensionar para textura de alta definição (2048 de largura mantendo a proporção exata do MDT)
    aspect = depth_m / width_m
    target_w = 2048
    target_h = int(round(target_w * aspect))

    img = Image.fromarray(np.transpose(rgb, (1, 2, 0)))
    img_resized = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    # Leve calibração de contraste e brilho para o renderizador 3D
    enhancer = ImageEnhance.Contrast(img_resized)
    img_enhanced = enhancer.enhance(1.18)
    brightener = ImageEnhance.Brightness(img_enhanced)
    img_enhanced = brightener.enhance(1.10)

    buf = io.BytesIO()
    img_enhanced.save(buf, format='JPEG', quality=88)
    b64_orto = base64.b64encode(buf.getvalue()).decode('utf-8')
    print(f"Ortofoto codificada em Base64 ({target_w}x{target_h} px, ~{round(len(b64_orto)/1024)} KB)")

    # 3. Carregar Mesas Solares do GPKG
    print("3. Carregando usinas fotovoltaicas...")
    tables_data = []
    for setor in ['p1', 'p2', 'p3']:
        gdf = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor}')
        for _, r in gdf.iterrows():
            geom = r.geometry
            c = geom.centroid
            tables_data.append({
                'setor': setor.upper(),
                'id': int(r['mesa_id']),
                'x': round(c.x - cx, 2),
                'y': round(r['cota_painel_inferior_m'] - z_min, 2),
                'z': round(-(c.y - cy), 2),
                'w': float(r['largura_m']),
                'd': float(r['comprimento_m']),
                'cota': float(r['cota_terreno_m'])
            })

    # 4. Salão e Campo
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

    # 5. Limite da Propriedade (Polígono)
    gdf_limite = gpd.read_file(GPKG_PATH, layer='limite_sitio').iloc[0]
    limite_coords = []
    for x, y in gdf_limite.geometry.exterior.coords:
        # Calcular cota aproximada no MDT para a linha 3D
        col_idx = int(round((x - bounds.left) / (bounds.right - bounds.left) * (cols - 1)))
        row_idx = int(round((bounds.top - y) / (bounds.top - bounds.bottom) * (rows - 1)))
        col_idx = max(0, min(cols - 1, col_idx))
        row_idx = max(0, min(rows - 1, row_idx))
        h = float(elev_clean[row_idx, col_idx]) - z_min + 1.2 # 1,2m acima do solo
        limite_coords.append({
            'x': round(x - cx, 2),
            'y': round(h, 2),
            'z': round(-(y - cy), 2)
        })

    print("4. Montando HTML do Visualizador 3D com Base64...")
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Visualizador 3D — Sítio das Andorinhas (Nativo SIGSC)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #0b111e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
    #canvas-container {{ width: 100vw; height: 100vh; }}
    
    #panel {{
      position: absolute; top: 16px; left: 16px; width: 350px;
      background: rgba(15, 23, 42, 0.88); color: #f8fafc; padding: 20px;
      border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      border: 1px solid rgba(255,255,255,0.12); backdrop-filter: blur(12px);
      z-index: 10;
    }}
    h1 {{ font-size: 16px; font-weight: 700; margin-bottom: 2px; color: #38bdf8; letter-spacing: 0.5px; }}
    .badge {{ display: inline-block; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; background: #0284c7; color: #fff; margin-bottom: 12px; }}
    .stat-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }}
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
      background: rgba(15, 23, 42, 0.92); color: #38bdf8; padding: 24px 36px;
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
  <div id="loading"><div class="spinner"></div>Renderizando Modelo SIGSC 3D...</div>
  <div id="canvas-container"></div>
  
  <div id="panel">
    <h1>SÍTIO DAS ANDORINHAS 3D</h1>
    <div class="badge">MDT 1,0 m + Ortofoto 0,39 m Oficial SIGSC</div>
    
    <div class="stat-row"><span class="stat-lbl">Área da Propriedade:</span><span class="stat-val">18,60 ha</span></div>
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
      <button class="btn btn-accent" onclick="toggleWireframe()">⚡ Alternar Ortofoto / Wireframe</button>
      <button class="btn btn-secondary" onclick="toggleBoundary()">🟡 Mostrar/Ocultar Limite do Sítio</button>
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
    const ortoBase64 = "data:image/jpeg;base64,{b64_orto}";

    // Setup Three.js
    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xd9e5ec); // Céu diurno suave
    scene.fog = new THREE.FogExp2(0xd9e5ec, 0.0004);

    const camera = new THREE.PerspectiveCamera(42, window.innerWidth / window.innerHeight, 2, 8000);
    camera.position.set(-150, 420, 520);

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
    controls.maxPolarAngle = Math.PI / 2 - 0.03;
    controls.target.set(0, 40, 0);

    // Iluminação balanceada e natural
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x64748b, 0.85);
    hemiLight.position.set(0, 600, 0);
    scene.add(hemiLight);

    const sun = new THREE.DirectionalLight(0xfff8ed, 1.15);
    sun.position.set(-300, 800, -250);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.camera.near = 100;
    sun.shadow.camera.far = 2500;
    sun.shadow.camera.left = -600;
    sun.shadow.camera.right = 600;
    sun.shadow.camera.top = 400;
    sun.shadow.camera.bottom = -400;
    scene.add(sun);

    // Luz de preenchimento para sombras suaves
    const fillLight = new THREE.DirectionalLight(0xb0c4de, 0.4);
    fillLight.position.set(300, 400, 400);
    scene.add(fillLight);

    // 1. Geometria do Terreno 3D
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

    // 2. Carregar a Textura da Ortofoto via Base64 (zero CORS, funciona localmente em qualquer navegador)
    const texture = new THREE.Texture();
    const ortoImage = new Image();
    ortoImage.onload = function() {{
      texture.image = ortoImage;
      texture.encoding = THREE.sRGBEncoding;
      if (renderer.capabilities && renderer.capabilities.getMaxAnisotropy) {{
        texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
      }}
      texture.needsUpdate = true;
      const el = document.getElementById('loading');
      if (el) el.style.display = 'none';
      renderer.render(scene, camera);
    }};
    ortoImage.src = ortoBase64;
    if (ortoImage.complete) {{
      ortoImage.onload();
    }}

    const matTerrain = new THREE.MeshStandardMaterial({{
      color: 0xffffff,
      map: texture,
      roughness: 0.85,
      metalness: 0.05,
      side: THREE.DoubleSide
    }});
    const terrain = new THREE.Mesh(geom, matTerrain);
    terrain.receiveShadow = true;
    scene.add(terrain);

    // 3. Linha 3D do Limite do Sítio das Andorinhas
    const boundaryPoints = [];
    limiteCoords.forEach(p => {{
      boundaryPoints.push(new THREE.Vector3(p.x, p.y, p.z));
    }});
    const boundaryGeom = new THREE.BufferGeometry().setFromPoints(boundaryPoints);
    const boundaryMat = new THREE.LineBasicMaterial({{ color: 0xffcc00, linewidth: 2 }});
    const boundaryLine = new THREE.Line(boundaryGeom, boundaryMat);
    scene.add(boundaryLine);

    // 4. Usinas Solares Solo (P1, P2, P3)
    const solarGroup = new THREE.Group();
    // Mesa fotovoltaica com 14 módulos bifaciais
    const tableGeom = new THREE.BoxGeometry(8.0, 0.22, 4.32);
    tableGeom.rotateX(THREE.MathUtils.degToRad(20)); // Inclinação 20° Norte

    // Materiais
    const moduleMat = new THREE.MeshStandardMaterial({{
      color: 0x1d4ed8,
      metalness: 0.8,
      roughness: 0.2
    }});

    const postMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, metalness: 0.6, roughness: 0.4 }});
    const postGeom = new THREE.CylinderGeometry(0.08, 0.08, 1.6, 6);

    tables.forEach(t => {{
      const mesaMesh = new THREE.Mesh(tableGeom, moduleMat);
      mesaMesh.position.set(t.x, t.y + 1.25, t.z);
      mesaMesh.castShadow = true;
      solarGroup.add(mesaMesh);

      // Postes dianteiro e traseiro
      const postFront = new THREE.Mesh(postGeom, postMat);
      postFront.position.set(t.x - 2.5, t.y + 0.6, t.z + 1.4);
      solarGroup.add(postFront);

      const postBack = new THREE.Mesh(postGeom, postMat);
      postBack.position.set(t.x + 2.5, t.y + 1.0, t.z - 1.4);
      solarGroup.add(postBack);
    }});
    scene.add(solarGroup);

    // 5. Salão de Eventos (Telhado Reto + Solar)
    const salaoGroup = new THREE.Group();
    const salaoBody = new THREE.Mesh(
      new THREE.BoxGeometry(11.0, 3.5, 8.11),
      new THREE.MeshStandardMaterial({{ color: 0xf1f5f9, roughness: 0.7 }})
    );
    salaoBody.position.set(salao.x, salao.y + 1.75, salao.z);
    salaoBody.castShadow = true;
    salaoBody.receiveShadow = true;
    salaoGroup.add(salaoBody);

    // Laje com Platibanda
    const platibanda = new THREE.Mesh(
      new THREE.BoxGeometry(11.2, 0.4, 8.3),
      new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.5 }})
    );
    platibanda.position.set(salao.x, salao.y + 3.7, salao.z);
    salaoGroup.add(platibanda);

    // 18 Módulos de Telhado do Salão (2 fileiras de 9)
    const roofModuleGeom = new THREE.BoxGeometry(1.15, 0.08, 2.38);
    roofModuleGeom.rotateX(THREE.MathUtils.degToRad(18));
    for (let row = 0; row < 2; row++) {{
      for (let col = 0; col < 9; col++) {{
        const rm = new THREE.Mesh(roofModuleGeom, moduleMat);
        const rx = salao.x - 4.8 + col * 1.2;
        const rz = salao.y ? (salao.z - 1.6 + row * 3.2) : salao.z;
        rm.position.set(rx, salao.y + 4.15, rz);
        salaoGroup.add(rm);
      }}
    }}
    scene.add(salaoGroup);

    // 6. Campo de Areia com Redes 3D
    const campoGroup = new THREE.Group();
    const sandMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 0.18, 12.0),
      new THREE.MeshStandardMaterial({{ color: 0xfde047, roughness: 0.95 }})
    );
    sandMesh.position.set(campo.x, campo.y + 0.1, campo.z);
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    // Redes perimetrais semi-transparentes
    const netMesh = new THREE.Mesh(
      new THREE.BoxGeometry(22.0, 6.0, 12.0),
      new THREE.MeshBasicMaterial({{ color: 0x334155, wireframe: true, transparent: true, opacity: 0.4 }})
    );
    netMesh.position.set(campo.x, campo.y + 3.0, campo.z);
    campoGroup.add(netMesh);
    scene.add(campoGroup);

    // Navegação de Câmera Suave
    function focusOn(target) {{
      if (target === 'p1') {{
        const t0 = tables[0];
        controls.target.set(t0.x + 30, t0.y + 10, t0.z);
        camera.position.set(t0.x - 50, t0.y + 55, t0.z + 100);
      }} else if (target === 'p2') {{
        const p2Table = tables.find(t => t.setor === 'P2') || tables[0];
        controls.target.set(p2Table.x + 20, p2Table.y, p2Table.z);
        camera.position.set(p2Table.x - 60, p2Table.y + 60, p2Table.z + 90);
      }} else if (target === 'p3') {{
        const p3Table = tables.find(t => t.setor === 'P3') || tables[0];
        controls.target.set(p3Table.x, p3Table.y, p3Table.z);
        camera.position.set(p3Table.x - 40, p3Table.y + 40, p3Table.z + 70);
      }} else if (target === 'salao') {{
        controls.target.set(salao.x, salao.y, salao.z);
        camera.position.set(salao.x - 45, salao.y + 30, salao.z + 65);
      }} else {{
        controls.target.set(0, 30, 0);
        camera.position.set(-150, 420, 520);
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
        f.write(html_content)
    print(f"Visualizador 3D Web Atualizado com Sucesso: {HTML_OUT}")

if __name__ == '__main__':
    main()
