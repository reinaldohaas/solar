#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Atualiza visualizador_3d_sitio.html refletindo com exatidão as construções de visualizador_casa_arredores.html:
1. Casa do Sítio (200 m², telhado1 e telhado2 KMZ alinhados, cumeeira a 4,60m, paredes e piso de cerâmica)
2. Salão de Festas (12×8m = 96 m², 100% aberto, sem estacas atravessando o telhado, 3 opções e 36 módulos solares)
3. Quadra de Areia (22×12m, borda de madeira, 10 postes H=6m, telas Sul, Leste e Norte H=6m, lado Oeste aberto, rede)
4. Chalés 1 a 5 (22 m² cada, pilotis ancorados no relevo, varandas, e Chalés 4 e 5 girados na direção da Casa do Sítio)
5. Preserva 100% do simulador solar anual/diário, relevo MDT LiDAR 1,0 m e textura de voo do drone do sítio original.
6. Copia o resultado para index.html
"""

import os
import re
import shutil

SOLAR_DIR = r"C:\Users\haas\github\solar"
HTML_SITIO = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")
HTML_INDEX = os.path.join(SOLAR_DIR, "index.html")

def main():
    print("================================================================================")
    print("REFLETINDO CONSTRUÇÕES DE visualizador_casa_arredores.html NO visualizador_3d_sitio.html")
    print("================================================================================")

    with open(HTML_SITIO, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. ATUALIZAR HUD PANEL (Remover visualizador_campo_salao e Opção 4 de refletores)
    # Substituir botões de opções do complexo
    old_opt_buttons = """      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-bottom: 8px;">
        <button class="btn btn-secondary btn-opt btn-opt-active" id="btnOpt1" onclick="setComplexOption(1)">🪵 1. Madeira Bruta</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt2" onclick="setComplexOption(2)">🏗️ 2. Metal 2 Águas</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt3" onclick="setComplexOption(3)">📐 3. 1 Água (Terreno)</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt4" onclick="setComplexOption(4)">💡 4. Arena Noturna</button>
      </div>"""

    new_opt_buttons = """      <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; margin-bottom: 8px;">
        <button class="btn btn-secondary btn-opt btn-opt-active" id="btnOpt1" onclick="setComplexOption(1)">🪵 1. Madeira Rústica</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt2" onclick="setComplexOption(2)">🏗️ 2. Metálica 2 Águas</button>
        <button class="btn btn-secondary btn-opt" id="btnOpt3" onclick="setComplexOption(3)">📐 3. 1 Água (Declive)</button>
      </div>"""

    if old_opt_buttons in content:
        content = content.replace(old_opt_buttons, new_opt_buttons)
        print("   [HUD] Botões de opções do salão atualizados para 3 opções sem refletores pretos.")

    # Substituir link de visualizador_campo_salao por visualizador_casa_arredores
    old_link = """      <a href="visualizador_campo_salao.html" target="_blank" class="btn btn-secondary" style="width: 100%; margin-top: 5px; font-size: 11px; text-decoration: none; display: flex; align-items: center; justify-content: center; background: #0f766e; border-color: #14b8a6; color: white;">
        🚀 Abrir Visualizador Dedicado (Salão & Campo 3D)
      </a>"""

    new_link = """      <a href="visualizador_casa_arredores.html" target="_blank" class="btn btn-secondary" style="width: 100%; margin-top: 5px; font-size: 11px; text-decoration: none; display: flex; align-items: center; justify-content: center; background: #0284c7; border-color: #38bdf8; color: white;">
        🏡 Abrir Visualizador Detalhado (Casa do Sítio & Arredores)
      </a>"""

    if old_link in content:
        content = content.replace(old_link, new_link)
        print("   [HUD] Link atualizado para visualizador_casa_arredores.html.")

    # Adicionar botões de foco na Casa e Chalés
    old_focus_buttons = """      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3 (46 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Geral</button>"""

    new_focus_buttons = """      <button class="btn btn-secondary" onclick="focusOn('casa')">🏠 Focar na Casa do Sítio (200 m²)</button>
      <button class="btn btn-secondary" onclick="focusOn('salao')">🏛️ Focar no Salão & Quadra</button>
      <button class="btn btn-secondary" onclick="focusOn('chales')">🏡 Focar nos Chalés 1 a 5 (22 m²)</button>
      <button class="btn btn-secondary" onclick="focusOn('p3')">🔎 Focar no Setor P3 (46 mesas)</button>
      <button class="btn btn-secondary" onclick="focusOn('geral')">🌐 Visão Panorâmica Geral</button>"""

    if old_focus_buttons in content:
        content = content.replace(old_focus_buttons, new_focus_buttons)
        print("   [HUD] Câmeras rápidas para Casa e Chalés adicionadas.")

    # 2. DECLARAÇÃO DAS COORDENADAS DE CASA E CHALÉS
    old_defs = 'const campo = {"x": -38.5, "y": 162.84, "z": -13.82, "cota": 547.56};'
    new_defs = """const campo = {"x": -38.5, "y": 162.84, "z": -13.82, "cota": 547.56};
    const casa = {"x": salao.x - 30.10, "y": salao.y - 5.90, "z": salao.z + 6.30, "cota": 540.95, "cx_utm": 663415.50, "cy_utm": 6968636.50};
    const chalesData = [
      {"id": 1, "x": salao.x + 11.69, "y": salao.y + 4.81, "z": salao.z - 32.16, "cota": 551.91},
      {"id": 2, "x": salao.x + 2.94,  "y": salao.y + 2.63, "z": salao.z - 24.28, "cota": 549.73},
      {"id": 3, "x": salao.x - 6.67,  "y": salao.y - 0.03, "z": salao.z - 16.46, "cota": 547.07},
      {"id": 4, "x": salao.x + 21.05, "y": salao.y + 1.92, "z": salao.z + 24.80, "cota": 549.02},
      {"id": 5, "x": salao.x + 24.09, "y": salao.y + 2.30, "z": salao.z + 42.26, "cota": 549.40}
    ];"""

    if old_defs in content:
        content = content.replace(old_defs, new_defs)
        print("   [DATA] Coordenadas de Casa e Chalés 1 a 5 inseridas.")

    # 3. SUBSTITUIR O BLOCO COMPLEXGROUP
    # Ponto inicial do bloco
    start_marker = "// 7. COMPLEXO INTEGRADO: SALÃO 12×8m (96 m²) & CAMPO DE FUTEBOL DE AREIA (22×12m)"
    # Ponto final do bloco
    end_marker = "// 9. ESFERA SOLAR VISÍVEL NO CÉU"

    idx_start = content.find(start_marker)
    idx_end = content.find(end_marker)

    if idx_start == -1 or idx_end == -1:
        print("ERRO: Marcadores de complexGroup não encontrados!")
        return

    new_complex_code = """// 7. COMPLEXO INTEGRADO 100% BASEADO EM visualizador_casa_arredores.html:
    //    CASA DO SÍTIO (200 m²), SALÃO 12x8m (36 MÓDULOS SOLARES), QUADRA 22x12m (TELAS H=6m) E CHALÉS 1 A 5
    const complexGroup = new THREE.Group();
    scene.add(complexGroup);

    // Textura Procedural de Telhas Cerâmicas Coloniais (Idêntica a visualizador_casa_arredores.html)
    function createClayTileTextures() {
      const w = 512, h = 512;
      const cDiff = document.createElement('canvas'); cDiff.width = w; cDiff.height = h;
      const ctx = cDiff.getContext('2d');
      const cBump = document.createElement('canvas'); cBump.width = w; cBump.height = h;
      const ctxB = cBump.getContext('2d');
      const colW = w / 12, rowH = h / 7;

      const imgD = ctx.createImageData(w, h); const d = imgD.data;
      const imgB = ctxB.createImageData(w, h); const b = imgB.data;

      for (let py = 0; py < h; py++) {
        const rowIdx = Math.floor(py / rowH);
        const ry = (py % rowH) / rowH;
        const overlapShadow = ry < 0.11 ? (0.62 + 0.38 * (ry / 0.11)) : 1.0;
        const overlapBump = (1.0 - ry) * 35;

        for (let px = 0; px < w; px++) {
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
        }
      }
      ctx.putImageData(imgD, 0, 0); ctxB.putImageData(imgB, 0, 0);

      const mapTex = new THREE.CanvasTexture(cDiff);
      mapTex.wrapS = THREE.RepeatWrapping; mapTex.wrapT = THREE.RepeatWrapping;
      const bumpTex = new THREE.CanvasTexture(cBump);
      bumpTex.wrapS = THREE.RepeatWrapping; bumpTex.wrapT = THREE.RepeatWrapping;
      return { mapTex, bumpTex };
    }

    const clayTextures = createClayTileTextures();

    // -------------------------------------------------------------------------
    // A) CASA DO SÍTIO: 200 m² ALINHADA A TELHADO 1 & TELHADO 2 KMZ
    // -------------------------------------------------------------------------
    const casaGroup = new THREE.Group();
    casaGroup.position.set(casa.x, casa.y, casa.z);
    complexGroup.add(casaGroup);

    (function buildCasaSitioKMZ() {
      const cxU = casa.cx_utm;
      const cyU = casa.cy_utm;
      const Rs = [663412.325, 6968630.679];
      const Rn = [663415.673, 6968642.764];
      const uE = 0.266982, uN = 0.963702;
      const nE = 0.963702, nN = -0.266982;
      const H_RIDGE = 4.60;
      const S_WEST = 0.34;
      const S_EAST = 0.235;

      function roofMetrics(e, n) {
        const along = (e - Rs[0]) * uE + (n - Rs[1]) * uN;
        const perp = (e - Rs[0]) * nE + (n - Rs[1]) * nN;
        const h = (perp <= 0) ? (H_RIDGE - S_WEST * Math.abs(perp)) : (H_RIDGE - S_EAST * perp);
        return { lx: e - cxU, lz: -(n - cyU), along: along, perp: perp, h: h };
      }

      // Vértices Exatos telhado1.kmz (Ala Oeste)
      const t1UTM = [
        [663408.675, 6968631.318], Rs, Rn,
        [663411.758, 6968643.518], [663408.972, 6968633.456], [663407.240, 6968633.914]
      ];
      const t1P = t1UTM.map(pt => roofMetrics(pt[0], pt[1]));

      const t1Geom = new THREE.BufferGeometry();
      const t1Pos = [], t1Uvs = [];
      const t1Tris = [[0, 1, 2], [0, 2, 3], [0, 3, 4], [0, 4, 5]];
      t1Tris.forEach(tri => {
        tri.forEach(vi => {
          t1Pos.push(t1P[vi].lx, t1P[vi].h, t1P[vi].lz);
          t1Uvs.push(t1P[vi].along * 0.22, t1P[vi].perp * 0.28);
        });
      });
      t1Geom.setAttribute('position', new THREE.Float32BufferAttribute(t1Pos, 3));
      t1Geom.setAttribute('uv', new THREE.Float32BufferAttribute(t1Uvs, 2));
      t1Geom.computeVertexNormals();

      const roofMatOeste = new THREE.MeshStandardMaterial({
        map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.045,
        roughness: 0.72, metalness: 0.08, side: THREE.DoubleSide
      });
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
      [[0, 1, 2], [0, 2, 3]].forEach(tri => {
        tri.forEach(vi => {
          t2Pos.push(t2P[vi].lx, t2P[vi].h, t2P[vi].lz);
          t2Uvs.push(t2P[vi].along * 0.22, t2P[vi].perp * 0.28);
        });
      });
      t2Geom.setAttribute('position', new THREE.Float32BufferAttribute(t2Pos, 3));
      t2Geom.setAttribute('uv', new THREE.Float32BufferAttribute(t2Uvs, 2));
      t2Geom.computeVertexNormals();

      const roofMatLeste = new THREE.MeshStandardMaterial({
        map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.045,
        roughness: 0.72, metalness: 0.08, side: THREE.DoubleSide
      });
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
      casaGroup.add(new THREE.Line(cumLineGeom, new THREE.LineBasicMaterial({ color: 0x7c2d12, linewidth: 3 })));

      // Paredes e Piso
      const wallPts = [
        [-7.3, -4.5], [-3.18, -5.82], [5.0, -8.19], [8.76, 3.89],
        [0.17, 6.26], [-3.74, 7.02], [-6.53, -3.04], [-8.26, -2.59]
      ];
      const floorShape = new THREE.Shape();
      wallPts.forEach((p, idx) => {
        if (idx === 0) floorShape.moveTo(p[0], -p[1]);
        else floorShape.lineTo(p[0], -p[1]);
      });
      const floorGeom = new THREE.ShapeGeometry(floorShape);
      floorGeom.rotateX(Math.PI / 2);
      const floorMesh = new THREE.Mesh(floorGeom, new THREE.MeshStandardMaterial({ color: 0x9a3412, roughness: 0.8 }));
      floorMesh.position.y = 0.05;
      casaGroup.add(floorMesh);

      const wallMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.85 });
      const wallGeom = new THREE.BufferGeometry();
      const wallVerts = [];
      for (let i = 0; i < wallPts.length; i++) {
        const cur = wallPts[i];
        const nxt = wallPts[(i + 1) % wallPts.length];
        const h1 = 2.80, h2 = 2.80;
        wallVerts.push(
          cur[0], 0, cur[1],  nxt[0], 0, nxt[1],  nxt[0], h2, nxt[1],
          cur[0], 0, cur[1],  nxt[0], h2, nxt[1], cur[0], h1, cur[1]
        );
      }
      wallGeom.setAttribute('position', new THREE.Float32BufferAttribute(wallVerts, 3));
      wallGeom.computeVertexNormals();
      casaGroup.add(new THREE.Mesh(wallGeom, wallMat));
    })();

    // -------------------------------------------------------------------------
    // B) SALÃO 12x8m: 100% ABERTO COM 36 MÓDULOS SOLARES FOTOVOLTAICOS
    // -------------------------------------------------------------------------
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salao.x, salao.y, salao.z);
    salaoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(salaoGroup);

    const matFloorConcrete = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.6 });
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.0, 0.25, 8.0), matFloorConcrete);
    salaoFloor.position.y = 0.125;
    salaoGroup.add(salaoFloor);

    // Escadaria frontal ampla (3 degraus largos)
    for (let s = 1; s <= 3; s++) {
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), matFloorConcrete);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      salaoGroup.add(step);
    }

    // Função de criação de fileira solar
    function createSalaoSolarRow(numCols = 9, modW = 1.134, modL = 1.95) {
      const rowGroup = new THREE.Group();
      const gap = 0.03;
      const totalW = numCols * modW + (numCols - 1) * gap;
      const startX = -totalW / 2 + modW / 2;
      for (let c = 0; c < numCols; c++) {
        const x = startX + c * (modW + gap);
        const cell = new THREE.Mesh(new THREE.BoxGeometry(modW - 0.035, 0.04, modL - 0.035), moduleMat);
        cell.position.set(x, 0.045, 0);
        cell.castShadow = true;
        rowGroup.add(cell);
      }
      return rowGroup;
    }

    const opt1Group = new THREE.Group();
    const opt2Group = new THREE.Group();
    const opt3Group = new THREE.Group();
    salaoGroup.add(opt1Group, opt2Group, opt3Group);

    // OPÇÃO 1: MADEIRA RÚSTICA (2 Águas com 36 módulos solares)
    const rusticWoodMat = new THREE.MeshStandardMaterial({ color: 0x4a2e18, roughness: 0.85 });
    const tileCeramicMat = new THREE.MeshStandardMaterial({
      map: clayTextures.mapTex, bumpMap: clayTextures.bumpTex, bumpScale: 0.05, roughness: 0.72
    });

    const pilarPositions = [
      [-5.7, 1.85, -3.7], [0, 1.85, -3.7], [5.7, 1.85, -3.7],
      [-5.7, 1.85, 3.7],  [0, 1.85, 3.7],  [5.7, 1.85, 3.7]
    ];
    pilarPositions.forEach(p => {
      const pMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.18, 3.6, 12), rusticWoodMat);
      pMesh.position.set(p[0], p[1], p[2]);
      pMesh.castShadow = true;
      opt1Group.add(pMesh);
    });

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

    // OPÇÃO 2: METÁLICA (2 Águas)
    const steelDarkMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.8, roughness: 0.3 });
    const panelSandwichMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.5, roughness: 0.4 });
    pilarPositions.forEach(p => {
      const pSteel = new THREE.Mesh(new THREE.BoxGeometry(0.20, 3.6, 0.20), steelDarkMat);
      pSteel.position.set(p[0], p[1], p[2]);
      opt2Group.add(pSteel);
    });
    const roofSteelBack = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelBack.rotation.x = -THREE.MathUtils.degToRad(18.0);
    roofSteelBack.position.set(0, 4.35, -2.15);
    const roofSteelFront = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.08, 4.6), panelSandwichMat);
    roofSteelFront.rotation.x = THREE.MathUtils.degToRad(18.0);
    roofSteelFront.position.set(0, 4.35, 2.15);
    opt2Group.add(roofSteelBack, roofSteelFront);

    // OPÇÃO 3: 1 ÁGUA (Declive Encosta)
    [-5.7, 0, 5.7].forEach(x => {
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.1, 0.2), steelDarkMat);
      pBack.position.set(x, 2.05, -3.7); opt3Group.add(pBack);
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 2.9, 0.2), steelDarkMat);
      pFront.position.set(x, 1.45, 3.7); opt3Group.add(pFront);
    });
    const roofMono = new THREE.Mesh(new THREE.BoxGeometry(13.0, 0.12, 9.4), panelSandwichMat);
    roofMono.rotation.x = THREE.MathUtils.degToRad(9.3);
    roofMono.position.set(0, 4.25, 0);
    opt3Group.add(roofMono);

    opt1Group.visible = true;
    opt2Group.visible = false;
    opt3Group.visible = false;

    // -------------------------------------------------------------------------
    // C) QUADRA DE AREIA 22x12m: TELAS DE PROTEÇÃO H=6m (LADO OESTE ABERTO)
    // -------------------------------------------------------------------------
    const campoGroup = new THREE.Group();
    campoGroup.position.set(campo.x, campo.y, campo.z);
    campoGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
    complexGroup.add(campoGroup);

    const sandMat = new THREE.MeshStandardMaterial({ color: 0xfde047, roughness: 0.95 });
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.30, 12.0), sandMat);
    sandMesh.position.y = 0.15;
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    const bordaMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.8 });
    const bordaMesh = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.40, 12.3), bordaMat);
    bordaMesh.position.y = 0.20;
    campoGroup.add(bordaMesh);

    // 10 Postes Metálicos de 6m
    const postMatQuadra = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.7, roughness: 0.3 });
    const quadraPostPositions = [
      [-11, -6], [-5.5, -6], [0, -6], [5.5, -6], [11, -6],
      [-11, 6], [-5.5, 6], [0, 6], [5.5, 6], [11, 6]
    ];
    quadraPostPositions.forEach(p => {
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.10, 0.10, 6.0, 8), postMatQuadra);
      pole.position.set(p[0], 3.0, p[1]);
      campoGroup.add(pole);
    });

    // Telas H = 6,00 m (Lado Oeste Aberto para a Casa)
    const telasGroup = new THREE.Group();
    campoGroup.add(telasGroup);

    const telaMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8, wireframe: true, transparent: true, opacity: 0.38, side: THREE.DoubleSide
    });

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

    // Cabo de Aço Superior (Sul, Leste, Norte)
    const cableMat = new THREE.LineBasicMaterial({ color: 0xe2e8f0, linewidth: 2 });
    const cablePts = [
      new THREE.Vector3(-11, 6.0, -6), new THREE.Vector3(11, 6.0, -6),
      new THREE.Vector3(11, 6.0, 6), new THREE.Vector3(-11, 6.0, 6)
    ];
    telasGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(cablePts), cableMat));

    // Rede Central Oficial de Jogo
    const netGameMat = new THREE.MeshBasicMaterial({ color: 0xffffff, wireframe: true, transparent: true, opacity: 0.75 });
    const net = new THREE.Mesh(new THREE.PlaneGeometry(8.5, 1.0), netGameMat);
    net.position.set(0, 2.2, 0);
    net.rotation.y = Math.PI / 2;
    campoGroup.add(net);

    // -------------------------------------------------------------------------
    // D) CHALÉS 1 A 5 (22 m² CADA): PILOTIS, DECK E CHALÉS 4 E 5 GIRADOS PARA A CASA
    // -------------------------------------------------------------------------
    const chaleWallMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.8 });
    const chaleRoofMat = new THREE.MeshStandardMaterial({ color: 0x9a3412, roughness: 0.7 });
    const chaleGlassMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.2, metalness: 0.8 });
    const chalePilarMat = new THREE.MeshStandardMaterial({ color: 0x475569, roughness: 0.9 });
    const chaleDeckMat = new THREE.MeshStandardMaterial({ color: 0x5c2d16, roughness: 0.75 });

    chalesData.forEach(c => {
      const cGroup = new THREE.Group();
      cGroup.position.set(c.x, c.y, c.z);
      if (c.id === 4 || c.id === 5) {
        // Chalés 4 e 5 girados diretamente para a Casa do Sítio
        cGroup.rotation.y = Math.atan2(casa.x - c.x, casa.z - c.z);
      } else {
        cGroup.rotation.y = -THREE.MathUtils.degToRad(28.02);
      }

      // Pilotis ancorados no relevo
      const pilotiCoords = [
        [-2.4, -1.8], [0.0, -1.8], [2.4, -1.8],
        [-2.4, 1.8],  [0.0, 1.8],  [2.4, 1.8]
      ];
      pilotiCoords.forEach(pt => {
        const pMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.16, 4.0, 8), chalePilarMat);
        pMesh.position.set(pt[0], -1.9, pt[1]);
        pMesh.castShadow = true;
        cGroup.add(pMesh);
      });

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
      const railMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.5 });
      const railFront = new THREE.Mesh(new THREE.BoxGeometry(5.40, 0.90, 0.06), railMat);
      railFront.position.set(0, 0.65, 1.95);
      const railL = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railL.position.set(-2.67, 0.65, 1.35);
      const railR = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.90, 1.20), railMat);
      railR.position.set(2.67, 0.65, 1.35);
      cGroup.add(railFront, railL, railR);

      // Janela panorâmica de vidro
      const win = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.8), chaleGlassMat);
      win.position.set(0, 1.45, 0.86);
      cGroup.add(win);

      complexGroup.add(cGroup);
    });
\n    """

    content = content[:idx_start] + new_complex_code + content[idx_end:]
    print("   [3D] complexGroup substituído com sucesso pelos modelos de visualizador_casa_arredores.html.")

    # 4. ATUALIZAR FUNÇÕES setComplexOption E focusOn
    old_set_option_func = """    function setComplexOption(opt) {
      currentOption = opt;
      opt1Group.visible = (opt === 1);
      opt2Group.visible = (opt === 2);
      opt3Group.visible = (opt === 3);
      opt4Group.visible = (opt === 4);

      pilarBaseGroup.visible = (opt !== 1);

      // Refletores de LED da Opção 4
      floodLightsList.forEach(light => {
        light.intensity = (opt === 4) ? 1.4 : 0.0;
      });

      // Atualizar botões HUD
      for (let i = 1; i <= 4; i++) {
        const btn = document.getElementById('btnOpt' + i);
        if (btn) {
          btn.classList.toggle('btn-opt-active', i === opt);
        }
      }

      document.getElementById('badgeOpcao').innerText = 'OPÇÃO ' + opt;
      document.getElementById('descOpcao').innerHTML = optionDescriptions[opt];
    }"""

    new_set_option_func = """    const optionDescriptions = {
      1: "<b>Opção 1: Madeira Rústica (Duas Águas)</b><br>Pilares de tora de eucalipto tratado (Ø26cm), tesouras de madeira rústica e telhas cerâmicas terracota com 36 módulos solares fotovoltaicos (18 na água Sul + 18 na água Norte). 100% aberto sem paredes.",
      2: "<b>Opção 2: Estrutura Metálica (Duas Águas)</b><br>Pilares e vigas em perfil de aço escuro com telhas termoacústicas sandwich e 36 módulos solares fotovoltaicos.",
      3: "<b>Opção 3: Telhado 1 Água (Declive da Encosta)</b><br>Cobertura mono-inclinada descendo no sentido da encosta e quadra de areia."
    };

    function setComplexOption(opt) {
      currentOption = opt;
      opt1Group.visible = (opt === 1);
      opt2Group.visible = (opt === 2);
      opt3Group.visible = (opt === 3);

      for (let i = 1; i <= 3; i++) {
        const btn = document.getElementById('btnOpt' + i);
        if (btn) {
          btn.classList.toggle('btn-opt-active', i === opt);
        }
      }

      document.getElementById('badgeOpcao').innerText = 'OPÇÃO ' + opt;
      document.getElementById('descOpcao').innerHTML = optionDescriptions[opt];
    }"""

    # Localizar e substituir setComplexOption
    if "function setComplexOption(opt) {" in content:
        # Encontrar o início de let currentOption
        opt_start = content.find("let currentOption = 1;")
        opt_end = content.find("function focusOnComplex() {")
        if opt_start != -1 and opt_end != -1:
            content = content[:opt_start] + "let currentOption = 1;\n" + new_set_option_func + "\n\n    " + content[opt_end:]
            print("   [JS] setComplexOption atualizado para 3 opções.")

    # Atualizar focusOn para incluir 'casa' e 'chales'
    old_focus_on = """      } else if (target === 'salao') {
        focusOnComplex();
      } else {"""

    new_focus_on = """      } else if (target === 'salao') {
        focusOnComplex();
      } else if (target === 'casa') {
        controls.target.set(casa.x, casa.y + 2.5, casa.z);
        camera.position.set(casa.x + 28, casa.y + 16, casa.z + 32);
      } else if (target === 'chales') {
        controls.target.set(salao.x + 5, salao.y + 4, salao.z - 25);
        camera.position.set(salao.x + 40, salao.y + 24, salao.z - 45);
      } else {"""

    if old_focus_on in content:
        content = content.replace(old_focus_on, new_focus_on)
        print("   [JS] Câmeras focusOn('casa') e focusOn('chales') adicionadas.")

    with open(HTML_SITIO, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"5. Arquivo visualizador_3d_sitio.html salvo ({os.path.getsize(HTML_SITIO):,} bytes)")

    # Copiar para index.html
    shutil.copyfile(HTML_SITIO, HTML_INDEX)
    print(f"6. Arquivo index.html atualizado ({os.path.getsize(HTML_INDEX):,} bytes)")
    print("================================================================================")

if __name__ == "__main__":
    main()
