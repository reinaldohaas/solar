"""
Script Definitivo: Visualizador 3D Dedicado do Complexo
Campo de Areia 22x12m & Salão 12x8m (Sem Paredes)
Sítio das Andorinhas - Santa Catarina

Implementações Conforme Pedido do Usuário:
1. ROTAÇÃO DE 3 GRAUS À DIREITA (Ângulo 31.02°):
   - Quadra de areia e Salão rotacionados exatamente 3° à direita (28.02° + 3.0° = 31.02°).
   - Torres de iluminação e cortes de terraplanagem recalculados na nova rotação.
2. CORTE NO RELEVO NO BARRANCO E NA ÁREA DA QUADRA:
   - Corte no barranco atrás do salão (cota 546.80m) criando o platô da edificação e canaleta.
   - Corte na área da quadra de areia (cota 547.20m), eliminando o morro que antes subia
     acima da quadra (548.08m > 547.56m). Agora o relevo fica nivelado sob a areia.
3. REMOÇÃO TOTAL DOS PAINÉIS SOBRE O SALÃO & ESTRUTURA LIMPA:
   - NENHUM painel sobre o salão ("Não há painéis sobre o salão").
   - Estrutura de madeira corrigida: escoras que furavam a cobertura foram removidas e o pendural
     foi rebaixado para ficar perfeitamente sob a cumeeira, sem nenhuma haste saindo do telhado.
4. TEXTURA DE DRONE HD TOTALMENTE SEM CORTES:
   - Abertura de todo o envelope do voo do drone 2026 (236m x 164m).
   - Ortofoto de Drone 2026 HD e Hipsometria DSM 2026 integradas perfeitamente sem corte arbitrário
     e com bordas suavizadas sobre o mosaico SIGSC.
"""

import os
import json
import base64
from io import BytesIO
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
from PIL import Image

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_MDT_TIF = r"C:\Users\haas\github\SIGSC\raster\mdt_sigsc\MDT_SG-22-Z-D-I-3-SE-A.tif"
SIGSC_ORTO_TIF = r"C:\Users\haas\github\SIGSC\raster\ortofoto_sigsc\Orto-RGB_SG-22-Z-D-I-3-SE-A.tif"
DRONE_ORTO_TIF = os.path.join(SOLAR_DIR, "Ortofoto_Drone_2026_Completo.tif")
DRONE_DSM_TIF = os.path.join(SOLAR_DIR, "DSM_Drone_2026_Completo.tif")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_campo_salao.html")

def apply_earthwork_cut(elev_grid, half_w, half_h, rows, cols, salao_x, salao_z, campo_x, campo_z, cota_cut=546.80, cota_cut_quadra=547.20):
    """
    Aplica escavação / terraplanagem no relevo:
    1. Salão e corte no barranco atrás do prédio (cota 546.80m)
    2. Platô da quadra de areia (cota 547.20m), impedindo que o solo suba acima da areia (547.56m)
    Ambos alinhados no novo azimute rotacionado 3° à direita (31.02°).
    """
    cut_grid = np.copy(elev_grid)
    c_angle = np.radians(31.02)
    cos_a = np.cos(c_angle)
    sin_a = np.sin(c_angle)

    for r in range(rows):
        wz = -half_h + r * (2 * half_h / (rows - 1))
        for c in range(cols):
            wx = -half_w + c * (2 * half_w / (cols - 1))

            # --- 1. CORTE DO SALÃO E BARRANCO ---
            dx_s = wx - salao_x
            dz_s = wz - salao_z
            lx_s = dx_s * cos_a + dz_s * sin_a
            lz_s = -dx_s * sin_a + dz_s * cos_a

            # Platô do Salão (12x8m + folga)
            if abs(lx_s) <= 7.0 and -5.5 <= lz_s <= 5.0:
                cut_grid[r, c] = min(cut_grid[r, c], cota_cut)
            # Talude de corte posterior no barranco real existente
            elif abs(lx_s) <= 8.5 and -9.0 <= lz_s < -5.5:
                t = (-5.5 - lz_s) / 3.5
                t = np.clip(t, 0.0, 1.0)
                target_h = cota_cut + t * (elev_grid[r, c] - cota_cut)
                cut_grid[r, c] = min(cut_grid[r, c], target_h)
            # Taludes laterais salão
            elif 7.0 < abs(lx_s) <= 9.5 and -5.5 <= lz_s <= 5.0:
                t = (abs(lx_s) - 7.0) / 2.5
                t = np.clip(t, 0.0, 1.0)
                target_h = cota_cut + t * (elev_grid[r, c] - cota_cut)
                cut_grid[r, c] = min(cut_grid[r, c], target_h)

            # --- 2. CORTE DO RELEVO NA ÁREA DA QUADRA DE AREIA ---
            dx_q = wx - campo_x
            dz_q = wz - campo_z
            lx_q = dx_q * cos_a + dz_q * sin_a
            lz_q = -dx_q * sin_a + dz_q * cos_a

            # Platô da Quadra (22x12m com envelope de escavação 24x14m)
            if abs(lx_q) <= 12.0 and abs(lz_q) <= 7.0:
                cut_grid[r, c] = min(cut_grid[r, c], cota_cut_quadra)
            # Transição suave do talude perimetral da quadra
            elif abs(lx_q) <= 14.5 and abs(lz_q) <= 9.5:
                dist_x = max(0.0, abs(lx_q) - 12.0) / 2.5
                dist_z = max(0.0, abs(lz_q) - 7.0) / 2.5
                t = max(dist_x, dist_z)
                t = np.clip(t, 0.0, 1.0)
                target_h = cota_cut_quadra + t * (elev_grid[r, c] - cota_cut_quadra)
                cut_grid[r, c] = min(cut_grid[r, c], target_h)

    return cut_grid

def main():
    print("=== INICIANDO GERAÇÃO DO VISUALIZADOR 3D: CORTE DUPLO + GIRO 3° + DRONE SEM CORTES ===")

    # Centro do voo completo do drone 2026 (abrangendo todo o complexo sem recortes arbitrários)
    cx_complex = 663397.5
    cy_complex = 6968625.0

    half_w = 118.0
    half_h = 82.0
    box_left = cx_complex - half_w
    box_right = cx_complex + half_w
    box_bottom = cy_complex - half_h
    box_top = cy_complex + half_h

    # 1. Leitura MDT SIGSC Oficial
    print("1. Extraindo MDT LiDAR Oficial do SIGSC (1,0 m nativo)...")
    with rasterio.open(SIGSC_MDT_TIF) as src_s:
        win_s = from_bounds(box_left, box_bottom, box_right, box_top, src_s.transform)
        sigsc_raw = src_s.read(1, window=win_s)
        sigsc_elev = np.array(sigsc_raw, dtype=np.float32).copy()
        rows_m, cols_m = sigsc_elev.shape

    # Posições 3D relativas ao centro expandido
    salao_3d_x = round(663449.59 - cx_complex, 2)  # 52.09
    salao_3d_z = round(-(6968652.91 - cy_complex), 2)  # -27.91
    campo_3d_x = round(663468.93 - cx_complex, 2)  # 71.43
    campo_3d_z = round(-(6968640.32 - cy_complex), 2)  # -15.32

    cota_salao = 547.32
    cota_cut = 546.80
    cota_quadra = 547.56
    cota_cut_quadra = 547.20

    # 2. Aplicar Terraplanagem (Barranco atrás do salão + Base da quadra)
    print("2. Aplicando Corte de Terraplanagem no Barranco e na Quadra de Areia...")
    sigsc_cut = apply_earthwork_cut(
        sigsc_elev, half_w, half_h, rows_m, cols_m,
        salao_3d_x, salao_3d_z, campo_3d_x, campo_3d_z,
        cota_cut, cota_cut_quadra
    )

    z_min_global = float(min(sigsc_cut.min(), sigsc_elev.min()))
    z_max_global = float(max(sigsc_cut.max(), sigsc_elev.max()))
    z_range_global = float(z_max_global - z_min_global)

    u16_sigsc_cut = ((sigsc_cut - z_min_global) / z_range_global * 65535.0).clip(0, 65535).astype(np.uint16)
    u16_sigsc_nat = ((sigsc_elev - z_min_global) / z_range_global * 65535.0).clip(0, 65535).astype(np.uint16)

    b64_sigsc_cut = base64.b64encode(u16_sigsc_cut.tobytes()).decode('utf-8')
    b64_sigsc_nat = base64.b64encode(u16_sigsc_nat.tobytes()).decode('utf-8')

    # 3. Geração das Texturas HD Sem Cortes Arbitrários
    print("3. Processando Texturas HD (SIGSC, Ortofoto Drone 2026 Completa e DSM KMZ)...")
    target_w = 1800
    target_h = int(1800 * (rows_m / cols_m))
    dst_transform = rasterio.transform.from_bounds(box_left, box_bottom, box_right, box_top, target_w, target_h)

    # A) Fundo Ortofoto Oficial SIGSC
    with rasterio.open(SIGSC_ORTO_TIF) as src_orto:
        win_o = from_bounds(box_left, box_bottom, box_right, box_top, src_orto.transform)
        rgb_sigsc = src_orto.read([1, 2, 3], window=win_o)
        img_sigsc_pil = Image.fromarray(np.transpose(rgb_sigsc, (1, 2, 0))).resize((target_w, target_h), Image.LANCZOS)
        sigsc_arr = np.array(img_sigsc_pil)
        
        buf_s = BytesIO()
        img_sigsc_pil.save(buf_s, format='JPEG', quality=88)
        b64_sigsc_tex = base64.b64encode(buf_s.getvalue()).decode('utf-8')
        print(f"   Ortofoto SIGSC: {target_w}x{target_h} px ({len(b64_sigsc_tex)/1024:.1f} KB)")

    # B) Ortofoto Drone 2026 Completa (Reprojetada no canvas sem corte de voo, mesclada suavemente no SIGSC)
    drone_reproj = np.zeros((4, target_h, target_w), dtype=np.uint8)
    with rasterio.open(DRONE_ORTO_TIF) as src_do:
        for b in range(1, 4):
            reproject(
                source=rasterio.band(src_do, b),
                destination=drone_reproj[b-1],
                src_transform=src_do.transform,
                src_crs=src_do.crs,
                dst_transform=dst_transform,
                dst_crs=src_do.crs,
                resampling=Resampling.bilinear
            )
        if src_do.count >= 4:
            reproject(
                source=rasterio.band(src_do, 4),
                destination=drone_reproj[3],
                src_transform=src_do.transform,
                src_crs=src_do.crs,
                dst_transform=dst_transform,
                dst_crs=src_do.crs,
                resampling=Resampling.bilinear
            )
        else:
            mask = (drone_reproj[0] > 0) | (drone_reproj[1] > 0) | (drone_reproj[2] > 0)
            drone_reproj[3] = (mask * 255).astype(np.uint8)

    alpha_drone = drone_reproj[3].astype(np.float32) / 255.0
    comp_orto = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for c in range(3):
        comp_orto[:, :, c] = np.clip(sigsc_arr[:, :, c] * (1.0 - alpha_drone) + drone_reproj[c] * alpha_drone, 0, 255).astype(np.uint8)

    img_drone_comp = Image.fromarray(comp_orto)
    buf_do = BytesIO()
    img_drone_comp.save(buf_do, format='JPEG', quality=88)
    b64_drone_orto_tex = base64.b64encode(buf_do.getvalue()).decode('utf-8')
    print(f"   Ortofoto Drone 2026 Completa: {target_w}x{target_h} px ({len(b64_drone_orto_tex)/1024:.1f} KB)")

    # C) DSM Drone 2026 Completo (KMZ Hipsometria)
    drone_dsm_reproj = np.zeros((4, target_h, target_w), dtype=np.uint8)
    with rasterio.open(DRONE_DSM_TIF) as src_dd:
        for b in range(1, 5):
            reproject(
                source=rasterio.band(src_dd, b),
                destination=drone_dsm_reproj[b-1],
                src_transform=src_dd.transform,
                src_crs=src_dd.crs,
                dst_transform=dst_transform,
                dst_crs=src_dd.crs,
                resampling=Resampling.bilinear
            )

    alpha_dsm = drone_dsm_reproj[3].astype(np.float32) / 255.0
    comp_dsm = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for c in range(3):
        comp_dsm[:, :, c] = np.clip(sigsc_arr[:, :, c] * 0.35 * (1.0 - alpha_dsm) + drone_dsm_reproj[c] * alpha_dsm, 0, 255).astype(np.uint8)

    img_dsm_comp = Image.fromarray(comp_dsm)
    buf_dd = BytesIO()
    img_dsm_comp.save(buf_dd, format='JPEG', quality=88)
    b64_drone_dsm_tex = base64.b64encode(buf_dd.getvalue()).decode('utf-8')
    print(f"   DSM Drone 2026 Completo: {target_w}x{target_h} px ({len(b64_drone_dsm_tex)/1024:.1f} KB)")

    # Dados das Edificações
    salao_data = {
        'x': float(salao_3d_x),
        'y': float(round(cota_salao - z_min_global, 2)),
        'z': float(salao_3d_z),
        'cota_piso': float(cota_salao),
        'cota_cut': float(cota_cut),
        'rotation_deg': 31.02
    }

    campo_data = {
        'x': float(campo_3d_x),
        'y': float(round(cota_quadra - z_min_global, 2)),
        'z': float(campo_3d_z),
        'cota_areia': float(cota_quadra),
        'cota_cut': float(cota_cut_quadra),
        'rotation_deg': 31.02
    }

    salao_json = json.dumps(salao_data)
    campo_json = json.dumps(campo_data)

    print("4. Construindo Aplicação WebGL com Three.js...")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Complexo Salão 12×8m & Arena de Areia — Sítio das Andorinhas</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #080c14; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    #webgl-container {{ width: 100vw; height: 100vh; position: absolute; left: 0; top: 0; }}

    /* HUD Header */
    .hud-header {{
      position: absolute; top: 16px; left: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 15px 18px; color: #f8fafc; max-width: 440px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .hud-header h1 {{ font-size: 16.5px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
    .hud-header p {{ font-size: 12px; color: #94a3b8; margin-top: 5px; line-height: 1.45; }}
    
    .badge-container {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
    .badge {{
      font-size: 10.5px; padding: 3px 8px; border-radius: 6px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .badge-rot {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .badge-cut {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-drone {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }}
    .badge-clean {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}

    /* Painel de Controle de Terreno & Corte */
    .panel-terrain {{
      position: absolute; top: 16px; right: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px;
      padding: 15px 18px; color: #f8fafc; width: 335px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .panel-title {{ font-size: 13px; font-weight: 700; color: #e2e8f0; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }}
    
    .btn-toggle-cut {{
      width: 100%; background: #047857; border: 1px solid #10b981; color: #fff;
      padding: 9px 12px; border-radius: 8px; font-size: 11.5px; font-weight: 700;
      cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 10px; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }}
    .btn-toggle-cut.cut-off {{
      background: #334155; border-color: #475569; color: #94a3b8; box-shadow: none;
    }}

    .terrain-info {{
      background: #0f172a; border-radius: 6px; padding: 8px 10px;
      font-size: 11px; color: #94a3b8; line-height: 1.4; border-left: 3px solid #38bdf8;
    }}
    .terrain-info b {{ color: #e2e8f0; }}

    .btn-tex {{
      background: #1e293b; border: 1px solid #334155; color: #cbd5e1;
      padding: 6px 9px; border-radius: 6px; font-size: 10.5px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: left;
    }}
    .btn-tex:hover {{ background: #334155; color: #fff; }}
    .btn-tex.active {{ background: #0284c7; border-color: #38bdf8; color: #fff; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }}

    /* Painel de Opções Arquitetônicas */
    .panel-options {{
      position: absolute; bottom: 20px; left: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 14px 18px; color: #f8fafc; width: 440px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .opt-buttons {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }}
    .btn-opt {{
      background: #1e293b; border: 1px solid #334155; color: #cbd5e1;
      padding: 9px 10px; border-radius: 8px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: center;
    }}
    .btn-opt:hover {{ background: #334155; color: #fff; }}
    .btn-opt.active {{ background: #d97706; border-color: #f59e0b; color: #fff; box-shadow: 0 0 12px rgba(245, 158, 11, 0.4); }}

    /* Painel de Câmeras & Perspectivas */
    .panel-cameras {{
      position: absolute; bottom: 20px; right: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 14px 18px; color: #f8fafc; width: 335px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .cam-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 8px; }}
    .btn-cam {{
      background: #1e293b; border: 1px solid #334155; color: #94a3b8;
      padding: 7px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: center;
    }}
    .btn-cam:hover {{ background: #334155; color: #fff; }}

    /* Legenda de Cotas / Status */
    .hud-status {{
      position: absolute; top: 16px; left: 50%; transform: translateX(-50%); z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px;
      padding: 8px 18px; color: #cbd5e1; font-size: 11px; display: flex; align-items: center; gap: 14px;
      box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    }}
    .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: #22c55e; }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="webgl-container"></div>

  <!-- HUD Header -->
  <div class="hud-header">
    <h1>🏛️ Salão 12×8m & Arena de Areia</h1>
    <p>Complexo de Lazer • Sítio das Andorinhas<br>
    <b>Giro 3° à Direita (31.02°)</b> • <b>Corte no Barranco & Quadra</b> • <b>Telhado Limpo</b></p>
    <div class="badge-container">
      <span class="badge badge-rot">Giro 3° Direita (31.02°)</span>
      <span class="badge badge-cut">Corte Barranco & Quadra</span>
      <span class="badge badge-drone">Drone HD Sem Cortes</span>
      <span class="badge badge-clean">Telhado Tradicional Limpo</span>
    </div>
  </div>

  <!-- Status Bar -->
  <div class="hud-status">
    <div style="display: flex; align-items: center; gap: 6px;">
      <div class="status-dot" id="statusDot"></div>
      <span id="statusMdtText">Base: <b>Drone 2026 HD + SIGSC LiDAR</b></span>
    </div>
    <span style="opacity: 0.3;">|</span>
    <span>Piso Salão: <b>547.32 m</b></span>
    <span style="opacity: 0.3;">|</span>
    <span>Quadra de Areia: <b>547.56 m</b></span>
  </div>

  <!-- Painel de Controle de Terreno & Corte -->
  <div class="panel-terrain">
    <div class="panel-title">
      <span>Topografia & Terraplanagem</span>
      <span style="font-size: 10px; color: #10b981;">Platô Nivelado</span>
    </div>

    <!-- Toggle Corte de Terraplanagem -->
    <button class="btn-toggle-cut" id="btnToggleCut" onclick="toggleEarthworkCut()">
      <span>🚜 Corte de Terraplanagem</span>
      <span id="lblCutStatus">ATIVO (PLATÔS)</span>
    </button>

    <div class="terrain-info" id="terrainInfoBox" style="margin-bottom: 10px;">
      <b>Corte Executado:</b> Escavação no barranco atrás do salão (cota 546.80m) e rebaixamento do relevo na quadra (cota 547.20m), eliminando a invasão do solo sobre a areia.<br>
      <b>Alinhamento:</b> Girado 3° à direita (31.02°).
    </div>

    <!-- Seletor de Textura de Superfície -->
    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 9px;">
      <div style="font-size: 11px; font-weight: 700; color: #cbd5e1; margin-bottom: 6px; display: flex; justify-content: space-between;">
        <span>Camada de Superfície:</span>
        <span style="font-size: 10px; color: #38bdf8;" id="lblTexName">Drone Orto HD 2026</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 5px;">
        <button class="btn-tex active" id="btnTex_drone_orto" onclick="setTexture('drone_orto')">
          🚁 Drone 2026 HD Completo (Sem Cortes)
        </button>
        <button class="btn-tex" id="btnTex_sigsc" onclick="setTexture('sigsc')">
          🌱 Ortofoto Oficial SIGSC (0,39m)
        </button>
        <button class="btn-tex" id="btnTex_drone_dsm" onclick="setTexture('drone_dsm')">
          🗺️ Hipsometria DSM Drone 2026 (KMZ)
        </button>
      </div>
    </div>
  </div>

  <!-- Painel de Opções Arquitetônicas -->
  <div class="panel-options">
    <div class="panel-title">
      <span>Opções da Cobertura do Salão 12×8m</span>
      <span style="font-size: 10px; color: #f59e0b;">Sem Paredes</span>
    </div>
    <div class="opt-buttons">
      <button class="btn-opt active" id="btnOpt1" onclick="setOption(1)">
        🪵 1. Madeira Rústica (2 Águas)<br>
        <span style="font-size: 9px; opacity: 0.8;">Tesouras rústicas, tora & cerâmica</span>
      </button>
      <button class="btn-opt" id="btnOpt2" onclick="setOption(2)">
        🏗️ 2. Metálica Duas Águas<br>
        <span style="font-size: 9px; opacity: 0.8;">Perfil metálico & telha termoacústica</span>
      </button>
      <button class="btn-opt" id="btnOpt3" onclick="setOption(3)">
        📐 3. Telhado 1 Água (Declive)<br>
        <span style="font-size: 9px; opacity: 0.8;">Inclinado 9,3° com a encosta</span>
      </button>
      <button class="btn-opt" id="btnOpt4" onclick="setOption(4)">
        ⚽ 4. Arena Noturna (Refletores)<br>
        <span style="font-size: 9px; opacity: 0.8;">4 Torres LED ativas na areia</span>
      </button>
    </div>
  </div>

  <!-- Painel de Câmeras & Perspectivas -->
  <div class="panel-cameras">
    <div class="panel-title">
      <span>Câmeras & Perspectivas 3D</span>
    </div>
    <div class="cam-grid">
      <button class="btn-cam" onclick="setCameraView('geral')">🌐 Panorâmica</button>
      <button class="btn-cam" onclick="setCameraView('corte')">🚜 Ver o Corte</button>
      <button class="btn-cam" onclick="setCameraView('salao')">🏛️ No Salão</button>
      <button class="btn-cam" onclick="setCameraView('campo')">⚽ Na Quadra</button>
    </div>
  </div>

  <script>
    // --- 1. DADOS TÉCNICOS INJETADOS PELO PYTHON ---
    const COLS = {cols_m};
    const ROWS = {rows_m};
    const WIDTH = {half_w * 2.0};
    const HEIGHT = {half_h * 2.0};
    const Z_MIN = {z_min_global};
    const Z_RANGE = {z_range_global};
    
    const salaoData = {salao_json};
    const campoData = {campo_json};

    function decodeB64UInt16(b64) {{
      const bin = atob(b64);
      const len = bin.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
      return new Uint16Array(bytes.buffer);
    }}

    const u16SigscCut = decodeB64UInt16("{b64_sigsc_cut}");
    const u16SigscNat = decodeB64UInt16("{b64_sigsc_nat}");

    const numVerts = COLS * ROWS;
    const heightsSigscCut = new Float32Array(numVerts);
    const heightsSigscNat = new Float32Array(numVerts);

    const heightsCurrent = new Float32Array(numVerts);
    const heightsTarget = new Float32Array(numVerts);

    for (let i = 0; i < numVerts; i++) {{
      heightsSigscCut[i] = (u16SigscCut[i] / 65535.0) * Z_RANGE;
      heightsSigscNat[i] = (u16SigscNat[i] / 65535.0) * Z_RANGE;

      heightsCurrent[i] = heightsSigscCut[i];
      heightsTarget[i] = heightsSigscCut[i];
    }}

    // --- 2. CONFIGURAÇÃO THREE.JS ---
    const container = document.getElementById('webgl-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080c14);
    scene.fog = new THREE.FogExp2(0x080c14, 0.0035);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.5, 900);
    camera.position.set(salaoData.x - 38, salaoData.y + 26, salaoData.z + 45);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: "high-performance" }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.minDistance = 5;
    controls.maxDistance = 350;
    controls.target.set((salaoData.x + campoData.x) / 2, salaoData.y + 2, (salaoData.z + campoData.z) / 2);

    // Iluminação
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.65);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.25);
    sunLight.position.set(salaoData.x + 50, salaoData.y + 80, salaoData.z + 50);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 250;
    sunLight.shadow.camera.left = -80;
    sunLight.shadow.camera.right = 80;
    sunLight.shadow.camera.top = 80;
    sunLight.shadow.camera.bottom = -80;
    sunLight.shadow.bias = -0.0003;
    scene.add(sunLight);

    // --- 3. RELEVO 3D E TEXTURAS SEM CORTES (DRONE 2026 HD + DSM KMZ + SIGSC) ---
    const terrainGeom = new THREE.PlaneGeometry(WIDTH, HEIGHT, COLS - 1, ROWS - 1);
    terrainGeom.rotateX(-Math.PI / 2);

    const droneOrtoTex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_drone_orto_tex}');
    const sigscTex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_sigsc_tex}');
    const droneDsmTex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_drone_dsm_tex}');

    [droneOrtoTex, sigscTex, droneDsmTex].forEach(tex => {{
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    }});

    const terrainMat = new THREE.MeshStandardMaterial({{
      map: droneOrtoTex,
      roughness: 0.85,
      metalness: 0.05,
      flatShading: false
    }});

    const terrainMesh = new THREE.Mesh(terrainGeom, terrainMat);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    window.setTexture = function(type) {{
      document.querySelectorAll('.btn-tex').forEach(b => b.classList.remove('active'));
      const btn = document.getElementById('btnTex_' + type);
      if (btn) btn.classList.add('active');

      const lbl = document.getElementById('lblTexName');
      if (type === 'drone_orto') {{
        terrainMat.map = droneOrtoTex;
        if (lbl) lbl.innerText = 'Drone Orto HD 2026 (Sem Cortes)';
      }} else if (type === 'sigsc') {{
        terrainMat.map = sigscTex;
        if (lbl) lbl.innerText = 'Oficial SIGSC (0,39m)';
      }} else if (type === 'drone_dsm') {{
        terrainMat.map = droneDsmTex;
        if (lbl) lbl.innerText = 'Hipsometria DSM Drone 2026 (KMZ)';
      }}
      terrainMat.needsUpdate = true;
    }};

    const posAttr = terrainGeom.attributes.position;
    for (let i = 0; i < numVerts; i++) {{
      posAttr.setY(i, heightsCurrent[i]);
    }}
    terrainGeom.computeVertexNormals();
    posAttr.needsUpdate = true;

    // --- 4. QUADRA DE AREIA (22x12m) ROTACIONADA 31.02° ---
    function createSandTexture() {{
      const canvas = document.createElement('canvas');
      canvas.width = 512; canvas.height = 512;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#e5c287';
      ctx.fillRect(0, 0, 512, 512);

      const imgData = ctx.getImageData(0, 0, 512, 512);
      const d = imgData.data;
      for (let i = 0; i < d.length; i += 4) {{
        const grain = (Math.random() - 0.5) * 28;
        const wave = Math.sin(Math.floor(i / 2048) * 0.15) * 8;
        d[i] = Math.min(255, Math.max(0, d[i] + grain + wave));
        d[i+1] = Math.min(255, Math.max(0, d[i+1] + grain * 0.8 + wave));
        d[i+2] = Math.min(255, Math.max(0, d[i+2] + grain * 0.5));
      }}
      ctx.putImageData(imgData, 0, 0);

      const tex = new THREE.CanvasTexture(canvas);
      tex.wrapS = THREE.RepeatWrapping; tex.wrapT = THREE.RepeatWrapping;
      tex.repeat.set(4, 2.2);
      return tex;
    }}

    const campoGroup = new THREE.Group();
    campoGroup.position.set(campoData.x, campoData.y, campoData.z);
    campoGroup.rotation.y = -THREE.MathUtils.degToRad(31.02);
    scene.add(campoGroup);

    const sandTex = createSandTexture();
    const sandMat = new THREE.MeshStandardMaterial({{
      map: sandTex,
      roughness: 0.95,
      bumpMap: sandTex,
      bumpScale: 0.05
    }});
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.40, 12.0), sandMat);
    sandMesh.position.set(0, 0.15, 0);
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    // Contenção Perimetral de Madeira da Quadra
    const timberMat = new THREE.MeshStandardMaterial({{ color: 0x5c3a21, roughness: 0.8 }});
    const bord1 = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.50, 0.15), timberMat);
    bord1.position.set(0, 0.20, 6.05);
    const bord2 = new THREE.Mesh(new THREE.BoxGeometry(22.3, 0.50, 0.15), timberMat);
    bord2.position.set(0, 0.20, -6.05);
    const bord3 = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.50, 12.0), timberMat);
    bord3.position.set(11.1, 0.20, 0);
    const bord4 = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.50, 12.0), timberMat);
    bord4.position.set(-11.1, 0.20, 0);
    campoGroup.add(bord1, bord2, bord3, bord4);

    // Linhas demarcatórias
    const lineMat = new THREE.MeshBasicMaterial({{ color: 0x0284c7 }});
    const lineGeomH = new THREE.PlaneGeometry(20.0, 0.08); lineGeomH.rotateX(-Math.PI / 2);
    const line1 = new THREE.Mesh(lineGeomH, lineMat); line1.position.set(0, 0.36, 5.5);
    const line2 = new THREE.Mesh(lineGeomH, lineMat); line2.position.set(0, 0.36, -5.5);
    const lineGeomV = new THREE.PlaneGeometry(0.08, 11.0); lineGeomV.rotateX(-Math.PI / 2);
    const line3 = new THREE.Mesh(lineGeomV, lineMat); line3.position.set(10.0, 0.36, 0);
    const line4 = new THREE.Mesh(lineGeomV, lineMat); line4.position.set(-10.0, 0.36, 0);
    const lineMid = new THREE.Mesh(lineGeomV, lineMat); lineMid.position.set(0, 0.36, 0);
    campoGroup.add(line1, line2, line3, line4, lineMid);

    // Traves de Futebol
    function createGoal(isRight) {{
      const g = new THREE.Group();
      const pMat = new THREE.MeshStandardMaterial({{ color: 0xffffff, roughness: 0.3 }});
      const nMat = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, wireframe: true, transparent: true, opacity: 0.6 }});
      const pL = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.2), pMat); pL.position.set(0, 1.1, 1.5);
      const pR = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.2), pMat); pR.position.set(0, 1.1, -1.5);
      const cross = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 3.12), pMat); cross.rotation.x = Math.PI / 2; cross.position.set(0, 2.2, 0);
      const net = new THREE.Mesh(new THREE.BoxGeometry(0.9, 2.15, 3.0), nMat); net.position.set(isRight ? 0.45 : -0.45, 1.1, 0);
      g.add(pL, pR, cross, net);
      return g;
    }}
    const goalEast = createGoal(true); goalEast.position.set(10.0, 0.35, 0);
    const goalWest = createGoal(false); goalWest.position.set(-10.0, 0.35, 0);
    campoGroup.add(goalEast, goalWest);

    // --- 5. SALÃO 12x8m ROTACIONADO 31.02° ---
    const salaoGroup = new THREE.Group();
    salaoGroup.position.set(salaoData.x, salaoData.y, salaoData.z);
    salaoGroup.rotation.y = -THREE.MathUtils.degToRad(31.02);
    scene.add(salaoGroup);

    // Embasamento sólido de concreto ciclópico (descendo 2,5m até o solo firme)
    const foundationMat = new THREE.MeshStandardMaterial({{
      color: 0x64748b,
      roughness: 0.85,
      metalness: 0.1
    }});

    const salaoPlinth = new THREE.Mesh(new THREE.BoxGeometry(12.0, 2.50, 8.0), foundationMat);
    salaoPlinth.position.set(0, -1.13, 0);
    salaoPlinth.receiveShadow = true;
    salaoPlinth.castShadow = true;
    salaoGroup.add(salaoPlinth);

    // Piso Acabado
    const floorTileMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.5 }});
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.1, 0.15, 8.1), floorTileMat);
    salaoFloor.position.set(0, 0.125, 0);
    salaoFloor.receiveShadow = true;
    salaoGroup.add(salaoFloor);

    // Sapatas dos 6 pilares
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

    // Escadaria Frontal Ampla de Acesso à Areia (3 degraus de 6 metros)
    const stairMat = new THREE.MeshStandardMaterial({{ color: 0x78716c, roughness: 0.7 }});
    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), stairMat);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      step.receiveShadow = true;
      salaoGroup.add(step);
    }}

    // Muro de Corte e Canaleta de Drenagem da Encosta (Atrás do Salão)
    const cutWallMat = new THREE.MeshStandardMaterial({{ color: 0x57534e, roughness: 0.9 }});
    const cutRetainingWall = new THREE.Mesh(new THREE.BoxGeometry(14.0, 1.60, 0.40), cutWallMat);
    cutRetainingWall.position.set(0, 0.30, -5.2);
    cutRetainingWall.castShadow = true;
    salaoGroup.add(cutRetainingWall);

    const ditchMat = new THREE.MeshStandardMaterial({{ color: 0x3f3f46, roughness: 0.8 }});
    const ditch = new THREE.Mesh(new THREE.BoxGeometry(14.0, 0.15, 0.50), ditchMat);
    ditch.position.set(0, -0.40, -4.6);
    salaoGroup.add(ditch);

    // GRUPOS DAS 4 OPÇÕES ARQUITETÔNICAS (SEM PAINÉIS SOLARES SOBRE O SALÃO)
    const optGroup1 = new THREE.Group(); // Madeira Rústica Tradicional (Cumeeira no Centro)
    const optGroup2 = new THREE.Group(); // Metálica Duas Águas (Cumeeira no Centro)
    const optGroup3 = new THREE.Group(); // Telhado 1 Água (Inclinado com o Terreno)
    const optGroup4 = new THREE.Group(); // Arena Noturna (Holofotes)
    salaoGroup.add(optGroup1, optGroup2, optGroup3);
    scene.add(optGroup4);

    // =========================================================================
    // OPÇÃO 1: MADEIRA RÚSTICA — TELHADO LIMPO, SEM HASTES OU PAINÉIS
    // =========================================================================
    const rusticWoodMat = new THREE.MeshStandardMaterial({{ color: 0x452311, roughness: 0.85 }});
    const tileCeramicMat = new THREE.MeshStandardMaterial({{ color: 0xa04822, roughness: 0.7 }});
    const ridgeTileMat = new THREE.MeshStandardMaterial({{ color: 0x8a3818, roughness: 0.65 }});

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

    // 3 TESOURAS TRADICIONAIS COM GEOMETRIA LIMPA (SEM PEÇAS FURANDO A TELHA)
    [-5.7, 0, 5.7].forEach(x => {{
      const truss = new THREE.Group();
      truss.position.set(x, 0, 0);

      // Tirante inferior horizontal
      const tieBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 8.2, 10), rusticWoodMat);
      tieBeam.rotation.x = Math.PI / 2; tieBeam.position.set(0, 3.65, 0);
      truss.add(tieBeam);

      // Pendural Central Vertical (contido com folga sob a cumeeira: h=1.40m, topo Y=5.05m < cumeeira 5.15m)
      const kingPost = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.11, 1.40, 10), rusticWoodMat);
      kingPost.position.set(0, 4.35, 0);
      truss.add(kingPost);

      // Pernas da tesoura
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

    // Viga Mestra de Cumeeira Longitudinal (Z = 0, Y = 5.15m)
    const ridgeBeam = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.13, 13.2, 12), rusticWoodMat);
    ridgeBeam.rotation.z = Math.PI / 2;
    ridgeBeam.position.set(0, 5.15, 0);
    optGroup1.add(ridgeBeam);

    // Duas Águas Simétricas com Telha Cerâmica Nobre (Sem Painéis Solares)
    const roofSlopeBack = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofSlopeBack.rotation.x = -THREE.MathUtils.degToRad(21.8);
    roofSlopeBack.position.set(0, 4.45, -2.18);
    roofSlopeBack.castShadow = true;

    const roofSlopeFront = new THREE.Mesh(new THREE.BoxGeometry(13.2, 0.12, 4.70), tileCeramicMat);
    roofSlopeFront.rotation.x = THREE.MathUtils.degToRad(21.8);
    roofSlopeFront.position.set(0, 4.45, 2.18);
    roofSlopeFront.castShadow = true;
    optGroup1.add(roofSlopeBack, roofSlopeFront);

    // Capa de Cumeeira Cerâmica em Meia-Cana no Centro Exato (Z = 0)
    const ridgeCap = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 13.3, 16), ridgeTileMat);
    ridgeCap.rotation.z = Math.PI / 2;
    ridgeCap.position.set(0, 5.28, 0);
    ridgeCap.castShadow = true;
    optGroup1.add(ridgeCap);

    // =========================================================================
    // OPÇÃO 2: ESTRUTURA METÁLICA DUAS ÁGUAS COM CUMEEIRA NO CENTRO
    // =========================================================================
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

    // =========================================================================
    // OPÇÃO 3: TELHADO 1 ÁGUA INCLINADO COM O TERRENO (9,3° DECLIVE)
    // =========================================================================
    const opt3CeilingWood = new THREE.MeshStandardMaterial({{ color: 0x92400e, roughness: 0.6 }});
    [-5.7, 0, 5.7].forEach(x => {{
      const pBack = new THREE.Mesh(new THREE.BoxGeometry(0.2, 4.3, 0.2), steelDarkMat);
      pBack.position.set(x, 2.15, -3.7); pBack.castShadow = true; optGroup3.add(pBack);
      const pFront = new THREE.Mesh(new THREE.BoxGeometry(0.2, 3.0, 0.2), steelDarkMat);
      pFront.position.set(x, 1.5, 3.7); pFront.castShadow = true; optGroup3.add(pFront);
    }});

    const roofMonoGroup = new THREE.Group();
    roofMonoGroup.position.set(0, 3.65, 0);
    roofMonoGroup.rotation.x = THREE.MathUtils.degToRad(9.3);
    const roofMonoSlab = new THREE.Mesh(new THREE.BoxGeometry(12.8, 0.12, 9.2), panelSandwichMat);
    roofMonoSlab.castShadow = true;
    const roofMonoCeil = new THREE.Mesh(new THREE.BoxGeometry(12.7, 0.02, 9.1), opt3CeilingWood);
    roofMonoCeil.position.set(0, -0.07, 0);
    roofMonoGroup.add(roofMonoSlab, roofMonoCeil);
    optGroup3.add(roofMonoGroup);

    // =========================================================================
    // OPÇÃO 4: ARENA NOTURNA (4 TORRES DE REFLETORES LED ATIVOS ROTACIONADAS 31.02°)
    // =========================================================================
    const poleMat = new THREE.MeshStandardMaterial({{ color: 0x334155, metalness: 0.9, roughness: 0.2 }});
    const floodlights = [];
    const poleOffsets = [[11.5, 6.2], [-11.5, 6.2], [11.5, -6.2], [-11.5, -6.2]];

    poleOffsets.forEach(pos => {{
      const tower = new THREE.Group();
      const localP = new THREE.Vector3(pos[0], 0, pos[1]);
      localP.applyAxisAngle(new THREE.Vector3(0, 1, 0), -THREE.MathUtils.degToRad(31.02));
      localP.add(new THREE.Vector3(campoData.x, campoData.y, campoData.z));
      tower.position.copy(localP);

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
      spot.target.position.set(campoData.x, campoData.y, campoData.z);
      scene.add(spot.target);
      tower.add(spot);
      floodlights.push(spot);

      optGroup4.add(tower);
    }});

    optGroup1.visible = true;
    optGroup2.visible = false;
    optGroup3.visible = false;

    // --- 6. CONTROLES DE TERRA & MDT ---
    let isCutActive = true;
    let morphProgress = 1.0;

    function updateTargetHeights() {{
      const srcArray = isCutActive ? heightsSigscCut : heightsSigscNat;
      for (let i = 0; i < numVerts; i++) {{
        heightsTarget[i] = srcArray[i];
      }}
      morphProgress = 0.0;
    }}

    window.toggleEarthworkCut = function() {{
      isCutActive = !isCutActive;
      const btn = document.getElementById('btnToggleCut');
      const lbl = document.getElementById('lblCutStatus');
      const info = document.getElementById('terrainInfoBox');

      if (isCutActive) {{
        btn.classList.remove('cut-off');
        lbl.innerText = 'ATIVO (PLATÔS)';
        info.innerHTML = `<b>Corte Ativo:</b> Platô no barranco do salão (cota 546.80m) e rebaixo nivelado da quadra de areia (cota 547.20m).<br>
          <b>Alinhamento:</b> Girado 3° à direita (31.02°).`;
      }} else {{
        btn.classList.add('cut-off');
        lbl.innerText = 'DESATIVADO (NATURAL)';
        info.innerHTML = `<b>Terreno Natural:</b> Exibe a encosta e relevo original sem as escavações da obra.`;
      }}
      updateTargetHeights();
    }};

    // Opções Arquitetônicas
    let currentArchOption = 1;
    window.setOption = function(opt) {{
      currentArchOption = opt;
      document.querySelectorAll('.btn-opt').forEach(b => b.classList.remove('active'));
      document.getElementById('btnOpt' + opt).classList.add('active');

      optGroup1.visible = (opt === 1 || opt === 4);
      optGroup2.visible = (opt === 2);
      optGroup3.visible = (opt === 3);

      if (opt === 4) {{
        scene.background.set(0x030712);
        scene.fog.color.set(0x030712);
        sunLight.intensity = 0.1;
        hemiLight.intensity = 0.2;
        floodlights.forEach(l => l.intensity = 2.8);
      }} else {{
        scene.background.set(0x080c14);
        scene.fog.color.set(0x080c14);
        sunLight.intensity = 1.25;
        hemiLight.intensity = 0.65;
        floodlights.forEach(l => l.intensity = 0.0);
      }}
    }};

    // Câmeras Pré-definidas
    window.setCameraView = function(view) {{
      if (view === 'geral') {{
        camera.position.set(salaoData.x - 38, salaoData.y + 26, salaoData.z + 45);
        controls.target.set((salaoData.x + campoData.x) / 2, salaoData.y + 2, (salaoData.z + campoData.z) / 2);
      }} else if (view === 'corte') {{
        camera.position.set(salaoData.x - 14, salaoData.y + 7.0, salaoData.z - 13);
        controls.target.set(salaoData.x, salaoData.y + 2.5, salaoData.z);
      }} else if (view === 'salao') {{
        camera.position.set(salaoData.x - 4, salaoData.y + 2.2, salaoData.z);
        controls.target.set(campoData.x, campoData.y + 1.5, campoData.z);
      }} else if (view === 'campo') {{
        camera.position.set(campoData.x + 8, campoData.y + 2.5, campoData.z);
        controls.target.set(salaoData.x, salaoData.y + 2.5, salaoData.z);
      }}
    }};

    function animate() {{
      requestAnimationFrame(animate);

      if (morphProgress < 1.0) {{
        morphProgress += 0.05;
        if (morphProgress > 1.0) morphProgress = 1.0;

        for (let i = 0; i < numVerts; i++) {{
          heightsCurrent[i] = heightsCurrent[i] + (heightsTarget[i] - heightsCurrent[i]) * 0.18;
          posAttr.setY(i, heightsCurrent[i]);
        }}
        terrainGeom.computeVertexNormals();
        posAttr.needsUpdate = true;
      }}

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

    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    
    size_mb = os.path.getsize(HTML_OUT) / (1024 * 1024)
    print(f"\n Visualizador Atualizado com Sucesso!")
    print(f" Arquivo: {HTML_OUT} ({size_mb:.2f} MB)")
    print(f" Giro de 3° à direita: Azimute ajustado para 31.02°")
    print(f" Corte no barranco (cota {cota_cut}m) + Corte na quadra de areia (cota {cota_cut_quadra}m)")
    print(f" Painéis solares completamente removidos sobre o salão")
    print(f" Estrutura de madeira corrigida sem hastes ou pendurais furando as telhas")
    print(f" Drone HD completo e hipsometria DSM sem cortes arbitrários")

if __name__ == "__main__":
    main()
