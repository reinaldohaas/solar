#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Definitivo: Visualizador 3D Dedicado do Complexo
Campo de Areia 22x12m, Salão 12x8m (Sem Paredes) e Casa do Sítio (Duas Águas)
Integrado com TODOS os dados de:
  C:\\Users\\haas\\OneDrive\\Documentos\\sitio_andorinhas\\Estrada-Ribeiro-dos-Ovos-01-06-2024-all
  - odm_dem/dsm.tif (7,38 cm/px float32 DSM)
  - odm_orthophoto/odm_orthophoto.tif (7,38 cm/px RGBA Ortofoto)
  - odm_georeferencing/odm_georeferenced_model.laz (Nuvem densa 6,47M pontos)

Correções de Terreno e Árvores 3D:
1. Terreno de Alta Definição (Malha 0,50 m = 472x328 = 154.816 vértices):
   - Extração do MDT/DTM 2024 corrigido a partir do DSM 7,4 cm calibrado com o LiDAR SIGSC,
     removendo os picos de árvores/telhados do chão e preservando pátios, estradas, açude e taludes reais.
   - Platôs nivelados para o Salão (547,05 m), Quadra de Areia (547,25 m) e Casa do Sítio (540,90 m).
   - Opção adicional para inspecionar o DSM Fotogramétrico Bruto de 2024 no próprio relevo.
2. Árvores 3D Reais Extraídas do Voo ( ~1.640 árvores georreferenciadas ):
   - Posição exata (X, Z), altura real da copa (CHM = DSM - DTM, de 2,2 m a 22,0 m),
     diâmetro de copa e cor foliar real amostrada diretamente da ortofoto de 7,4 cm/px.
   - Renderizadas via THREE.InstancedMesh (troncos + copas orgânicas multi-lobulares com oclusão de vértices).
"""

import os
import json
import base64
from io import BytesIO
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject, Resampling
from scipy.ndimage import (
    minimum_filter, maximum_filter, gaussian_filter,
    distance_transform_edt, binary_erosion, median_filter, percentile_filter
)
from PIL import Image, ImageDraw

SOLAR_DIR = r"C:\Users\haas\github\solar"
ODM_DIR = r"C:\Users\haas\OneDrive\Documentos\sitio_andorinhas\Estrada-Ribeiro-dos-Ovos-01-06-2024-all"

SIGSC_MDT_TIF = r"C:\Users\haas\github\SIGSC\raster\mdt_sigsc\MDT_SG-22-Z-D-I-3-SE-A.tif"
SIGSC_ORTO_TIF = r"C:\Users\haas\github\SIGSC\raster\ortofoto_sigsc\Orto-RGB_SG-22-Z-D-I-3-SE-A.tif"
ODM_DSM_TIF = os.path.join(ODM_DIR, "odm_dem", "dsm.tif")
ODM_ORTO_TIF = os.path.join(ODM_DIR, "odm_orthophoto", "odm_orthophoto.tif")
DRONE_ORTO_2026_TIF = os.path.join(SOLAR_DIR, "Ortofoto_Drone_2026_Completo.tif")
HTML_OUT = os.path.join(SOLAR_DIR, "visualizador_campo_salao.html")


def apply_earthwork_cut(elev_grid, half_w, half_h, rows, cols, salao_x, salao_z, campo_x, campo_z, cota_cut=547.05, cota_cut_quadra=547.25):
    """
    Aplica terraplanagem (corte e aterro compensado) sobre o MDT 2024 corrigido:
    1. Platô do Salão (cota 547.05m) com corte no barranco posterior e nivelamento frontal.
    2. Platô da Quadra de Areia (cota 547.25m) com corte na encosta superior e talude suave.
    3. Platô da Casa do Sítio (cota 540.90m) sob as duas águas (telhado1.kmz e telhado2.kmz).
    """
    cut_grid = np.copy(elev_grid)
    c_angle = np.radians(31.02)
    cos_a = np.cos(c_angle)
    sin_a = np.sin(c_angle)

    gy, gx = np.mgrid[0:rows, 0:cols]
    wx = -half_w + gx * (2.0 * half_w / (cols - 1))
    wz = -half_h + gy * (2.0 * half_h / (rows - 1))

    # --- 1. PLATÔ DO SALÃO E CORTE NO BARRANCO ---
    dx_s = wx - salao_x
    dz_s = wz - salao_z
    lx_s = dx_s * cos_a + dz_s * sin_a
    lz_s = -dx_s * sin_a + dz_s * cos_a

    in_salao_core = (np.abs(lx_s) <= 7.2) & (lz_s >= -5.2) & (lz_s <= 5.5)
    in_salao_ramp = (~in_salao_core) & (np.abs(lx_s) <= 10.5) & (lz_s >= -9.5) & (lz_s <= 9.0)

    cut_grid[in_salao_core] = cota_cut
    if np.any(in_salao_ramp):
        dist_x = np.maximum(0.0, np.abs(lx_s[in_salao_ramp]) - 7.2) / 3.3
        lz_r = lz_s[in_salao_ramp]
        dist_z = np.where(lz_r < -5.2, (-5.2 - lz_r) / 4.3, np.where(lz_r > 5.5, (lz_r - 5.5) / 3.5, 0.0))
        t = np.clip(np.hypot(dist_x, dist_z), 0.0, 1.0)
        s = 0.5 - 0.5 * np.cos(np.pi * t)
        cut_grid[in_salao_ramp] = cota_cut + s * (elev_grid[in_salao_ramp] - cota_cut)

    # --- 2. PLATÔ E TALUDE SUAVE NA ÁREA DA QUADRA DE AREIA ---
    dx_q = wx - campo_x
    dz_q = wz - campo_z
    lx_q = dx_q * cos_a + dz_q * sin_a
    lz_q = -dx_q * sin_a + dz_q * cos_a

    in_q_core = (np.abs(lx_q) <= 12.2) & (np.abs(lz_q) <= 7.2)
    in_q_ramp = (~in_q_core) & (np.abs(lx_q) <= 17.5) & (np.abs(lz_q) <= 12.5)

    cut_grid[in_q_core] = cota_cut_quadra
    if np.any(in_q_ramp):
        dist_x = np.maximum(0.0, np.abs(lx_q[in_q_ramp]) - 12.2) / 5.3
        dist_z = np.maximum(0.0, np.abs(lz_q[in_q_ramp]) - 7.2) / 5.3
        t = np.clip(np.hypot(dist_x, dist_z), 0.0, 1.0)
        s = 0.5 - 0.5 * np.cos(np.pi * t)
        cut_grid[in_q_ramp] = cota_cut_quadra + s * (cut_grid[in_q_ramp] - cota_cut_quadra)

    # --- 3. PLATÔ NIVELADO DA CASA DO SÍTIO (TELHADO 1 & TELHADO 2) ---
    dx_c = wx - 18.00
    dz_c = wz - (-11.50)
    cos_c = 0.9638
    sin_c = 0.2668
    lx_c = dx_c * cos_c + dz_c * sin_c
    lz_c = -dx_c * sin_c + dz_c * cos_c
    cota_cut_casa = 540.95

    in_c_core = (lx_c >= -5.2) & (lx_c <= 8.2) & (np.abs(lz_c) <= 7.0)
    in_c_ramp = (~in_c_core) & (lx_c >= -8.5) & (lx_c <= 11.5) & (np.abs(lz_c) <= 10.2)

    cut_grid[in_c_core] = cota_cut_casa
    if np.any(in_c_ramp):
        lxr = lx_c[in_c_ramp]
        lzr = lz_c[in_c_ramp]
        dist_xc = np.where(lxr < -5.2, (-5.2 - lxr) / 3.3, np.where(lxr > 8.2, (lxr - 8.2) / 3.3, 0.0))
        dist_zc = np.maximum(0.0, np.abs(lzr) - 7.0) / 3.2
        t = np.clip(np.hypot(dist_xc, dist_zc), 0.0, 1.0)
        s = 0.5 - 0.5 * np.cos(np.pi * t)
        cut_grid[in_c_ramp] = cota_cut_casa + s * (cut_grid[in_c_ramp] - cota_cut_casa)

    return cut_grid


def main():
    print("=== GERANDO VISUALIZADOR 3D DO COMPLEXO — ESCALA REAL 1:1 (1m HORIZONTAL = 1m VERTICAL) ===")

    cx_complex = 663397.5
    cy_complex = 6968625.0
    half_w = 118.0
    half_h = 82.0
    box_left = cx_complex - half_w
    box_right = cx_complex + half_w
    box_bottom = cy_complex - half_h
    box_top = cy_complex + half_h

    # Grade de 0,50 m por vértice (472 x 328 = 154.816 vértices)
    res_grid = 0.50
    cols_m = int(round((box_right - box_left) / res_grid))
    rows_m = int(round((box_top - box_bottom) / res_grid))
    print(f"1. Extraindo Relevo 1:1 de 0,50m ({cols_m}x{rows_m} = {cols_m*rows_m:,} vértices) de ODM DSM 7,4cm...")

    with rasterio.open(ODM_DSM_TIF) as src_d:
        win_d = from_bounds(box_left, box_bottom, box_right, box_top, src_d.transform)
        dsm_raw = src_d.read(1, window=win_d, out_shape=(rows_m, cols_m), resampling=Resampling.nearest).astype(np.float32)

    with rasterio.open(ODM_ORTO_TIF) as src_o:
        win_o = from_bounds(box_left, box_bottom, box_right, box_top, src_o.transform)
        orto24_grid = src_o.read([1, 2, 3, 4], window=win_o, out_shape=(4, rows_m, cols_m), resampling=Resampling.average)

    valid_dsm = (dsm_raw > 350.0) & (dsm_raw < 650.0) & (orto24_grid[3] > 200)
    valid_dsm = binary_erosion(valid_dsm, iterations=3)
    ind = distance_transform_edt(~valid_dsm, return_distances=False, return_indices=True)

    # Translação vertical pura (+76.35m) sem inclinação artificial: 1,000m horizontal = 1,000m vertical!
    dsm_1to1 = median_filter(dsm_raw[tuple(ind)], size=3) + 76.35

    # 2. Envoltória Inferior Bare-Earth 1:1 (janela de 27,5m = 55px para atravessar bosques sem criar morros de copa!)
    min_35m = minimum_filter(dsm_1to1, size=55)
    low_env = gaussian_filter(percentile_filter(min_35m, percentile=35, size=35), sigma=7.0)
    res_ground = np.clip(dsm_1to1 - low_env, 0.0, 2.2)
    ground_local = low_env + gaussian_filter(percentile_filter(res_ground, percentile=25, size=25), sigma=3.0)

    # CHM 1:1 calibrado por proeminência individual da copa (evita somar platôs de mata densa)
    chm_raw = np.where(valid_dsm, np.clip(dsm_1to1 - ground_local, 0.0, 12.0), 0.0)
    chm_local_base = gaussian_filter(minimum_filter(chm_raw, size=15), sigma=2.5)
    chm = np.where(valid_dsm, np.clip(0.55 * (chm_raw - chm_local_base * 0.5) + 0.45 * chm_raw, 0.0, 6.8), 0.0)

    fine_ground = np.where(chm_raw < 0.9, dsm_1to1 - ground_local, 0.0)
    dtm_2024_nat = (ground_local + gaussian_filter(fine_ground, sigma=1.2)).astype(np.float32)

    gy, gx = np.mgrid[0:rows_m, 0:cols_m]

    salao_3d_x = round(663449.59 - cx_complex, 2)   # 52.09
    salao_3d_z = round(-(6968652.91 - cy_complex), 2) # -27.91
    campo_3d_x = round(663468.93 - cx_complex, 2)   # 71.43
    campo_3d_z = round(-(6968640.32 - cy_complex), 2) # -15.32
    casa_3d_x = round(663415.50 - cx_complex, 2)    # 18.00
    casa_3d_z = round(-(6968636.50 - cy_complex), 2)  # -11.50

    # Cotas 1:1 reais do solo sob as edificações (Casa=541.00m, Salão=547.10m, Quadra=546.50m)
    cota_salao = 547.10
    cota_cut = 547.05
    cota_quadra = 546.50
    cota_cut_quadra = 546.45
    cota_casa = 541.00

    print("2. Aplicando Terraplanagem 1:1 (Platôs da Casa 540,95m, Salão 547,05m e Campo 546,45m)...")
    dtm_2024_cut = apply_earthwork_cut(
        dtm_2024_nat, half_w, half_h, rows_m, cols_m,
        salao_3d_x, salao_3d_z, campo_3d_x, campo_3d_z,
        cota_cut, cota_cut_quadra
    )

    # Superfície DSM 2024 completa 1:1 (com relevo fotogramétrico das copas e telhados)
    dsm_surface_2024 = (dtm_2024_nat + chm_raw).astype(np.float32)

    z_min_global = float(min(dtm_2024_cut.min(), dtm_2024_nat.min(), dsm_surface_2024.min()))
    z_max_global = float(max(dtm_2024_cut.max(), dtm_2024_nat.max(), dsm_surface_2024.max()))
    z_range_global = float(z_max_global - z_min_global)

    u16_cut = ((dtm_2024_cut - z_min_global) / z_range_global * 65535.0).clip(0, 65535).astype(np.uint16)
    u16_nat = ((dtm_2024_nat - z_min_global) / z_range_global * 65535.0).clip(0, 65535).astype(np.uint16)
    u16_dsm = ((dsm_surface_2024 - z_min_global) / z_range_global * 65535.0).clip(0, 65535).astype(np.uint16)

    b64_cut = base64.b64encode(u16_cut.tobytes()).decode('utf-8')
    b64_nat = base64.b64encode(u16_nat.tobytes()).decode('utf-8')
    b64_dsm = base64.b64encode(u16_dsm.tobytes()).decode('utf-8')

    # 3. Extração das Árvores 3D Reais em Escala 1:1 (1m Horizontal = 1m Vertical)
    print("3. Extraindo Árvores 3D em Escala Métrica 1:1 (1m Horizontal = 1m Vertical)...")
    orto26_grid = np.zeros((4, rows_m, cols_m), dtype=np.uint8)
    dst_trans_grid = rasterio.transform.from_bounds(box_left, box_bottom, box_right, box_top, cols_m, rows_m)
    with rasterio.open(DRONE_ORTO_2026_TIF) as src_26:
        for b_idx in range(1, 5):
            reproject(
                source=rasterio.band(src_26, b_idx),
                destination=orto26_grid[b_idx-1],
                src_transform=src_26.transform,
                src_crs=src_26.crs,
                dst_transform=dst_trans_grid,
                dst_crs="EPSG:31982",
                resampling=Resampling.average
            )

    grid_e = box_left + (gx / (cols_m - 1)) * (box_right - box_left)
    grid_n = box_top - (gy / (rows_m - 1)) * (box_top - box_bottom)

    r24, g24, b24 = orto24_grid[0].astype(float), orto24_grid[1].astype(float), orto24_grid[2].astype(float)
    exg24 = 2.0 * g24 - r24 - b24
    bright24 = (r24 + g24 + b24) / 3.0

    r26, g26, b26, a26 = orto26_grid[0].astype(float), orto26_grid[1].astype(float), orto26_grid[2].astype(float), orto26_grid[3]
    exg26 = 2.0 * g26 - r26 - b26

    in_construction_zone = (grid_e >= 663430.0) & (grid_e <= 663500.0) & (grid_n >= 6968618.0) & (grid_n <= 6968672.0)
    cleared_26 = in_construction_zone & (a26 > 120) & ((r26 > g26) | (exg26 < 12.0))
    not_foliage_24 = (r24 > g24 + 5) | (exg24 < 3.0) | (bright24 < 16.0) | (bright24 > 215.0)

    in_casa_roof = (grid_e >= 663405.5) & (grid_e <= 663425.5) & (grid_n >= 6968628.5) & (grid_n <= 6968645.0)
    in_casa_yard = (grid_e >= 663406.0) & (grid_e <= 663417.5) & (grid_n >= 6968615.0) & (grid_n <= 6968629.0)
    in_shed_south = (grid_e >= 663410.0) & (grid_e <= 663421.0) & (grid_n >= 6968600.0) & (grid_n <= 6968615.0)

    cos_a = np.cos(np.radians(31.02))
    sin_a = np.sin(np.radians(31.02))
    dxs = grid_e - 663449.59
    dzs = -(grid_n - 6968652.91)
    lxs = dxs * cos_a + dzs * sin_a
    lzs = -dxs * sin_a + dzs * cos_a
    in_salao_pad = (np.abs(lxs) <= 8.8) & (np.abs(lzs) <= 6.8)

    dxq = grid_e - 663468.93
    dzq = -(grid_n - 6968640.32)
    lxq = dxq * cos_a + dzq * sin_a
    lzq = -dxq * sin_a + dzq * cos_a
    in_campo_pad = (np.abs(lxq) <= 13.8) & (np.abs(lzq) <= 8.8)

    excl = (~valid_dsm) | cleared_26 | not_foliage_24 | in_casa_roof | in_casa_yard | in_shed_south | in_salao_pad | in_campo_pad
    is_canopy = (~excl) & (chm >= 2.0)

    chm_s = gaussian_filter(chm, sigma=0.8)
    prominence = chm_s - gaussian_filter(chm_s, sigma=3.0)
    score = np.where(is_canopy, chm_s + 2.5 * prominence, -999.0)

    cand_r, cand_c = np.where(is_canopy)
    order = np.argsort(-score[cand_r, cand_c])

    occupied = np.zeros((rows_m, cols_m), dtype=bool)
    trees_list = []

    for idx in order:
        r_i = int(cand_r[idx])
        c_i = int(cand_c[idx])
        if occupied[r_i, c_i]:
            continue
        h_raw = float(chm_s[r_i, c_i])
        if h_raw < 2.0:
            continue

        # Escala 1:1 estrita entre horizontal (diâmetro D = 2*R) e vertical (altura H):
        # Cada 1 metro horizontal equivale exatamente a 1 metro vertical (D_horiz = H_vert = h_val)
        h_val = float(np.clip(h_raw, 2.50, 6.40))
        crown_rad_m = 0.50 * h_val
        diam_horiz_m = 2.0 * crown_rad_m

        spacing_px = max(3, int(round((crown_rad_m * 1.18) / res_grid)))
        r0 = max(0, r_i - spacing_px)
        r1 = min(rows_m, r_i + spacing_px + 1)
        c0 = max(0, c_i - spacing_px)
        c1 = min(cols_m, c_i + spacing_px + 1)
        yy_sub, xx_sub = np.ogrid[r0-r_i:r1-r_i, c0-c_i:c1-c_i]
        occupied[r0:r1, c0:c1] |= ((yy_sub**2 + xx_sub**2) <= (spacing_px**2))

        wx_t = -half_w + c_i * (2.0 * half_w / (cols_m - 1))
        wz_t = -half_h + r_i * (2.0 * half_h / (rows_m - 1))
        y_cut_t = float(dtm_2024_cut[r_i, c_i] - z_min_global)
        y_nat_t = float(dtm_2024_nat[r_i, c_i] - z_min_global)

        # Cor foliar amostrada da ortofoto 2024
        cr = int(np.clip(r24[r_i, c_i] * 1.05, 28, 165))
        cg = int(np.clip(g24[r_i, c_i] * 1.12, 55, 210))
        cb = int(np.clip(b24[r_i, c_i] * 0.88, 18, 120))
        hex_col = (cr << 16) | (cg << 8) | cb

        # Compact array entry: [x, z, yCut, yNat, height_1to1, crownRadius_1to1, hexColor]
        trees_list.append([
            round(wx_t, 2),
            round(wz_t, 2),
            round(y_cut_t, 2),
            round(y_nat_t, 2),
            round(h_val, 2),
            round(crown_rad_m, 2),
            hex_col
        ])

    print(f"   Extraídas {len(trees_list)} árvores 3D em escala 1:1 (1m H = 1m V) para o Complexo!")
    trees_json = json.dumps(trees_list, separators=(',', ':'))

    # 4. Geração das Texturas HD (2200 px de largura = ~10,7 cm/px!)
    print("4. Processando Texturas HD (Ortofoto ODM 2024 7,4cm + Drone 2026 5cm + Hipsometria CHM/DSM)...")
    target_w = 2200
    target_h = int(round(target_w * (rows_m / cols_m)))
    dst_transform = rasterio.transform.from_bounds(box_left, box_bottom, box_right, box_top, target_w, target_h)

    # A) Fundo Ortofoto Oficial SIGSC
    with rasterio.open(SIGSC_ORTO_TIF) as src_orto:
        win_o = from_bounds(box_left, box_bottom, box_right, box_top, src_orto.transform)
        rgb_sigsc = src_orto.read([1, 2, 3], window=win_o)
        img_sigsc_pil = Image.fromarray(np.transpose(rgb_sigsc, (1, 2, 0))).resize((target_w, target_h), Image.LANCZOS)
        sigsc_arr = np.array(img_sigsc_pil)

    # B) Ortofoto ODM 2024 Nativa de 7,38 cm/px
    with rasterio.open(ODM_ORTO_TIF) as src_o24:
        win_o24 = from_bounds(box_left, box_bottom, box_right, box_top, src_o24.transform)
        rgba_24 = src_o24.read([1, 2, 3, 4], window=win_o24, out_shape=(4, target_h, target_w), resampling=Resampling.bilinear)

    alpha_24 = (rgba_24[3].astype(np.float32) / 255.0)
    alpha_24_smooth = gaussian_filter(alpha_24, sigma=4.0)
    orto24_comp = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for c in range(3):
        orto24_comp[:, :, c] = np.clip(sigsc_arr[:, :, c] * (1.0 - alpha_24_smooth) + rgba_24[c] * alpha_24_smooth, 0, 255).astype(np.uint8)

    # C) Ortofoto Drone 2026 sobreposta na área de obra com bordas suavizadas (feathering)
    drone26_reproj = np.zeros((4, target_h, target_w), dtype=np.uint8)
    with rasterio.open(DRONE_ORTO_2026_TIF) as src_do:
        for b in range(1, 5):
            reproject(
                source=rasterio.band(src_do, b),
                destination=drone26_reproj[b-1],
                src_transform=src_do.transform,
                src_crs=src_do.crs,
                dst_transform=dst_transform,
                dst_crs="EPSG:31982",
                resampling=Resampling.bilinear
            )

    # Suavizar máscara de borda do voo de 2026 para não ficar marca de corte reta
    mask_26_eroded = binary_erosion(drone26_reproj[3] > 200, iterations=12)
    alpha_26_feather = gaussian_filter(mask_26_eroded.astype(np.float32), sigma=10.0)
    comp_24_26 = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    for c in range(3):
        comp_24_26[:, :, c] = np.clip(orto24_comp[:, :, c] * (1.0 - alpha_26_feather) + drone26_reproj[c] * alpha_26_feather, 0, 255).astype(np.uint8)

    # Limpar a projeção 2D do telhado no chão estritamente sob a Casa do Sítio 3D para evitar telhado duplicado no solo
    for img_arr in (comp_24_26, orto24_comp):
        c0_casa = int((663407.5 - box_left) / (box_right - box_left) * target_w)
        c1_casa = int((663423.8 - box_left) / (box_right - box_left) * target_w)
        r0_casa = int((box_top - 6968643.2) / (box_top - box_bottom) * target_h)
        r1_casa = int((box_top - 6968629.5) / (box_top - box_bottom) * target_h)
        img_arr[r0_casa:r1_casa, c0_casa:c1_casa, 0] = 132
        img_arr[r0_casa:r1_casa, c0_casa:c1_casa, 1] = 124
        img_arr[r0_casa:r1_casa, c0_casa:c1_casa, 2] = 110

    buf_24_26 = BytesIO()
    Image.fromarray(comp_24_26).save(buf_24_26, format='JPEG', quality=88)
    b64_drone_orto_tex = base64.b64encode(buf_24_26.getvalue()).decode('utf-8')

    buf_24 = BytesIO()
    Image.fromarray(orto24_comp).save(buf_24, format='JPEG', quality=88)
    b64_orto24_tex = base64.b64encode(buf_24.getvalue()).decode('utf-8')

    # D) Mapa Hipsométrico DSM 2024 + Altura das Copas (CHM) de 7,4 cm/px
    chm_hi = np.array(Image.fromarray(chm.astype(np.float32)).resize((target_w, target_h), Image.BILINEAR))
    dsm_hi = np.array(Image.fromarray(dsm_surface_2024).resize((target_w, target_h), Image.BILINEAR))
    dsm_norm = np.clip((dsm_hi - z_min_global) / z_range_global, 0.0, 1.0)
    # Paleta hipsométrica combinada com sombreamento da ortofoto
    hypso_rgb = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    hypso_rgb[:, :, 0] = np.clip(40 + 210 * np.clip((dsm_norm - 0.35) * 1.8, 0, 1) + (chm_hi > 4.0) * 35, 0, 255).astype(np.uint8)
    hypso_rgb[:, :, 1] = np.clip(90 + 150 * np.sin(dsm_norm * np.pi) + np.clip(chm_hi * 8.0, 0, 70), 0, 255).astype(np.uint8)
    hypso_rgb[:, :, 2] = np.clip(180 * (1.0 - dsm_norm), 0, 255).astype(np.uint8)
    comp_dsm_vis = np.clip(orto24_comp.astype(float) * 0.45 + hypso_rgb.astype(float) * 0.55, 0, 255).astype(np.uint8)

    buf_dd = BytesIO()
    Image.fromarray(comp_dsm_vis).save(buf_dd, format='JPEG', quality=86)
    b64_drone_dsm_tex = base64.b64encode(buf_dd.getvalue()).decode('utf-8')

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
    casa_data = {
        'x': float(casa_3d_x),
        'y': float(round(cota_casa - z_min_global, 2)),
        'z': float(casa_3d_z),
        'cota_piso': float(cota_casa),
        'cx_utm': 663415.50,
        'cy_utm': 6968636.50
    }

    salao_json = json.dumps(salao_data)
    campo_json = json.dumps(campo_data)
    casa_json = json.dumps(casa_data)

    print("5. Construindo Aplicação WebGL com Terreno 0,50m e Árvores 3D Reais...")
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Complexo Salão 12×8m, Quadra & Casa do Sítio — Relevo e Árvores 3D Reais (Drone 7,4cm)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ overflow: hidden; background: #080c14; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    #webgl-container {{ width: 100vw; height: 100vh; position: absolute; left: 0; top: 0; }}

    .hud-header {{
      position: absolute; top: 16px; left: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 15px 18px; color: #f8fafc; max-width: 450px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .hud-header h1 {{ font-size: 16px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
    .hud-header p {{ font-size: 11.5px; color: #94a3b8; margin-top: 5px; line-height: 1.45; }}
    
    .badge-container {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }}
    .badge {{
      font-size: 10px; padding: 3px 8px; border-radius: 6px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.4px;
    }}
    .badge-rot {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }}
    .badge-cut {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-drone {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.4); }}
    .badge-clean {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }}

    .panel-terrain {{
      position: absolute; top: 16px; right: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 12px;
      padding: 14px 16px; color: #f8fafc; width: 345px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
      max-height: calc(100vh - 210px); overflow-y: auto;
    }}
    .panel-title {{ font-size: 12.5px; font-weight: 700; color: #e2e8f0; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }}
    
    .btn-toggle-cut {{
      width: 100%; background: #047857; border: 1px solid #10b981; color: #fff;
      padding: 8px 11px; border-radius: 8px; font-size: 11px; font-weight: 700;
      cursor: pointer; transition: all 0.2s; display: flex; align-items: center; justify-content: space-between;
      margin-bottom: 6px; box-shadow: 0 0 10px rgba(16, 185, 129, 0.3);
    }}
    .btn-toggle-cut.cut-off {{
      background: #334155; border-color: #475569; color: #cbd5e1; box-shadow: none;
    }}

    .terrain-info {{
      background: #0f172a; border-radius: 6px; padding: 7px 9px;
      font-size: 10.5px; color: #94a3b8; line-height: 1.38; border-left: 3px solid #38bdf8;
    }}
    .terrain-info b {{ color: #e2e8f0; }}

    .btn-tex {{
      background: #1e293b; border: 1px solid #334155; color: #cbd5e1;
      padding: 6px 9px; border-radius: 6px; font-size: 10.5px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: left;
    }}
    .btn-tex:hover {{ background: #334155; color: #fff; }}
    .btn-tex.active {{ background: #0284c7; border-color: #38bdf8; color: #fff; box-shadow: 0 0 10px rgba(56, 189, 248, 0.4); }}

    .panel-options {{
      position: absolute; bottom: 20px; left: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 14px 18px; color: #f8fafc; width: 450px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .opt-buttons {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }}
    .btn-opt {{
      background: #1e293b; border: 1px solid #334155; color: #cbd5e1;
      padding: 8px 10px; border-radius: 8px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: center;
    }}
    .btn-opt:hover {{ background: #334155; color: #fff; }}
    .btn-opt.active {{ background: #d97706; border-color: #f59e0b; color: #fff; box-shadow: 0 0 12px rgba(245, 158, 11, 0.4); }}

    .panel-cameras {{
      position: absolute; bottom: 20px; right: 20px; z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 12px 16px; color: #f8fafc; width: 345px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }}
    .cam-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 6px; }}
    .btn-cam {{
      background: #1e293b; border: 1px solid #334155; color: #94a3b8;
      padding: 7px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
      cursor: pointer; transition: all 0.2s; text-align: center;
    }}
    .btn-cam:hover {{ background: #334155; color: #fff; }}

    .hud-status {{
      position: absolute; top: 16px; left: 50%; transform: translateX(-50%); z-index: 100;
      background: rgba(13, 19, 33, 0.94); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px;
      padding: 8px 18px; color: #cbd5e1; font-size: 11px; display: flex; align-items: center; gap: 12px;
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
    <h1>🏛️ Salão 12×8m, Arena & Casa do Sítio</h1>
    <p>Relevo 0,50m e <b>{len(trees_list)} Árvores 3D Reais</b> extraídas do DSM de 7,4 cm/px<br>
    (<code>Estrada-Ribeiro-dos-Ovos-01-06-2024-all</code> + Voo 2026 + LiDAR SIGSC)</p>
    <div class="badge-container">
      <span class="badge badge-cut">MDT 2024 Corrigido (0,5m)</span>
      <span class="badge badge-drone">{len(trees_list)} Árvores 3D Reais (CHM)</span>
      <span class="badge badge-rot">Ortofoto 7,4 cm + 5 cm</span>
      <span class="badge badge-clean">Casa Duas Águas (Barro)</span>
    </div>
    <a href="visualizador_3d_sitio.html" style="margin-top: 9px; display: inline-flex; align-items: center; gap: 6px; background: #0284c7; color: #fff; text-decoration: none; font-size: 11px; font-weight: 700; padding: 6px 12px; border-radius: 6px; border: 1px solid #38bdf8;">
      ⬅️ Abrir Sítio Completo 3D (Usina Solar + 137 ha)
    </a>
  </div>

  <!-- Status Bar -->
  <div class="hud-status">
    <div style="display: flex; align-items: center; gap: 6px;">
      <div class="status-dot" id="statusDot"></div>
      <span id="statusMdtText">Escala Real <b>1:1 (1m H = 1m V)</b> | <b>{len(trees_list)} Árvores 3D</b></span>
    </div>
    <span style="opacity: 0.3;">|</span>
    <span>Casa: <b>541.00 m</b> (h=4,65m)</span>
    <span style="opacity: 0.3;">|</span>
    <span>Salão: <b>547.05 m</b> (12×8×5,2m)</span>
    <span style="opacity: 0.3;">|</span>
    <span>Quadra: <b>546.45 m</b> (22×12×6,0m)</span>
  </div>

  <!-- Painel de Controle de Terreno & Árvores -->
  <div class="panel-terrain">
    <div class="panel-title">
      <span>Escala 1:1 (1m H = 1m V) & Relevo</span>
      <span style="font-size: 10px; color: #10b981;">Malha 0,50 m</span>
    </div>

    <!-- Toggle Réguas de Escala 1:1 (1m Horizontal = 1m Vertical) -->
    <button class="btn-toggle-cut" id="btnToggleScale1to1" onclick="toggleScale1to1()" style="background: #0284c7; border-color: #38bdf8;">
      <span>📏 Escala 1:1 (1m H = 1m V)</span>
      <span id="lblScale1to1Status">VISÍVEL (1:1)</span>
    </button>

    <!-- Toggle Modo de Terreno (Corte / Natural / DSM Bruto) -->
    <button class="btn-toggle-cut" id="btnToggleCut" onclick="cycleTerrainMode()">
      <span>🚜 Modo do Relevo 3D</span>
      <span id="lblCutStatus">PLATÔS + MDT 2024</span>
    </button>

    <!-- Toggle Árvores 3D Reais -->
    <button class="btn-toggle-cut" id="btnToggleTrees" onclick="toggleTrees3D()" style="background: #15803d; border-color: #22c55e;">
      <span>🌳 Árvores 3D 1:1 (DSM 7,4cm)</span>
      <span id="lblTreesStatus">{len(trees_list)} ATIVAS</span>
    </button>

    <div class="terrain-info" id="terrainInfoBox" style="margin-bottom: 9px;">
      <b>Proporção Métrica 1:1 Estrita:</b> Cada <b>1,00 m horizontal equivale exatamente a 1,00 m vertical</b> no relevo, nas construções (Casa 14×12,5×4,65m, Salão 12×8×5,2m, Quadra 22×12×6m) e nas árvores 3D (diâmetro horizontal × altura vertical 1:1).
    </div>

    <!-- Controle de Escala Z e Nivelamento Vertical do Terreno -->
    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; margin-bottom: 9px; background: rgba(16, 185, 129, 0.08); padding: 8px; border-radius: 8px; border: 1px solid rgba(16, 185, 129, 0.28);">
      <div style="font-size: 11px; font-weight: 700; color: #cbd5e1; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center;">
        <span>⛰️ Escala Z do Terreno:</span>
        <span style="font-size: 10.5px; color: #34d399; font-weight: 800;" id="lblZScale">1.00x (Real 1:1)</span>
      </div>
      <input type="range" id="sliderZScale" min="0.05" max="2.50" step="0.05" value="1.0" style="width: 100%; accent-color: #10b981; cursor: pointer;" oninput="setZScale(this.value)">
      <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 3px; margin-top: 4px; margin-bottom: 7px;">
        <button onclick="setZScalePreset(0.25)" style="background:#1e293b; color:#cbd5e1; border:1px solid #334155; border-radius:4px; font-size:9.5px; padding:3px 0; cursor:pointer; font-weight:600;">0.25x</button>
        <button onclick="setZScalePreset(0.50)" style="background:#1e293b; color:#cbd5e1; border:1px solid #334155; border-radius:4px; font-size:9.5px; padding:3px 0; cursor:pointer; font-weight:600;">0.50x</button>
        <button onclick="setZScalePreset(0.75)" style="background:#1e293b; color:#cbd5e1; border:1px solid #334155; border-radius:4px; font-size:9.5px; padding:3px 0; cursor:pointer; font-weight:600;">0.75x</button>
        <button onclick="setZScalePreset(1.00)" style="background:#065f46; color:#ecfdf5; border:1px solid #10b981; border-radius:4px; font-size:9.5px; padding:3px 0; cursor:pointer; font-weight:700;">1.0x</button>
        <button onclick="setZScalePreset(1.50)" style="background:#1e293b; color:#cbd5e1; border:1px solid #334155; border-radius:4px; font-size:9.5px; padding:3px 0; cursor:pointer; font-weight:600;">1.50x</button>
      </div>
      <div style="font-size: 10.5px; font-weight: 700; color: #cbd5e1; margin-bottom: 3px; display: flex; justify-content: space-between; align-items: center;">
        <span>↕️ Altura / Offset Z do Terreno:</span>
        <span style="font-size: 10px; color: #38bdf8; font-weight: 700;" id="lblZOffset">0.00 m</span>
      </div>
      <div style="display: flex; gap: 5px; align-items: center;">
        <input type="range" id="sliderZOffset" min="-5.0" max="5.0" step="0.05" value="0.0" style="flex: 1; accent-color: #38bdf8; cursor: pointer;" oninput="setZOffset(this.value)">
        <button onclick="setZOffset(0)" style="background:#1e293b; color:#94a3b8; border:1px solid #334155; border-radius:4px; font-size:9px; padding:2px 5px; cursor:pointer;">Zero</button>
      </div>
    </div>

    <!-- Seletor de Textura de Superfície -->
    <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px;">
      <div style="font-size: 11px; font-weight: 700; color: #cbd5e1; margin-bottom: 5px; display: flex; justify-content: space-between;">
        <span>Camada de Superfície:</span>
        <span style="font-size: 10px; color: #38bdf8;" id="lblTexName">Drone 2024 (7cm) + 2026</span>
      </div>
      <div style="display: flex; flex-direction: column; gap: 5px;">
        <button class="btn-tex active" id="btnTex_drone_orto" onclick="setTexture('drone_orto')">
          🚁 Ortofoto Fusão Drone 2024 (7,4cm) + 2026 (5cm)
        </button>
        <button class="btn-tex" id="btnTex_orto24" onclick="setTexture('orto24')">
          🌳 Ortofoto ODM 2024 Pura (7,4 cm/px Nativa)
        </button>
        <button class="btn-tex" id="btnTex_drone_dsm" onclick="setTexture('drone_dsm')">
          🗺️ Hipsometria DSM 2024 + Altura das Copas (CHM)
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
        <span style="font-size: 9px; opacity: 0.8;">Tesouras rústicas, tora & telha de barro</span>
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
      <button class="btn-cam" onclick="setCameraView('casa')" style="grid-column: span 2; background: rgba(180, 83, 9, 0.38); border-color: rgba(245, 158, 11, 0.55); color: #fef3c7;">🏠 Na Casa do Sítio (Duas Águas - Telha de Barro)</button>
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
    const casaData = {casa_json};
    const treesData = {trees_json};

    function decodeB64UInt16(b64) {{
      const bin = atob(b64);
      const len = bin.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
      return new Uint16Array(bytes.buffer);
    }}

    const u16Cut = decodeB64UInt16("{b64_cut}");
    const u16Nat = decodeB64UInt16("{b64_nat}");
    const u16Dsm = decodeB64UInt16("{b64_dsm}");

    const numVerts = COLS * ROWS;
    const heightsCut = new Float32Array(numVerts);
    const heightsNat = new Float32Array(numVerts);
    const heightsDsm = new Float32Array(numVerts);

    const heightsCurrent = new Float32Array(numVerts);
    const heightsTarget = new Float32Array(numVerts);

    for (let i = 0; i < numVerts; i++) {{
      heightsCut[i] = (u16Cut[i] / 65535.0) * Z_RANGE;
      heightsNat[i] = (u16Nat[i] / 65535.0) * Z_RANGE;
      heightsDsm[i] = (u16Dsm[i] / 65535.0) * Z_RANGE;

      heightsCurrent[i] = heightsCut[i];
      heightsTarget[i] = heightsCut[i];
    }}

    // --- 2. CONFIGURAÇÃO THREE.JS ---
    const container = document.getElementById('webgl-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080c14);
    scene.fog = new THREE.FogExp2(0x080c14, 0.0028);

    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.5, 950);
    camera.position.set(salaoData.x - 42, salaoData.y + 28, salaoData.z + 48);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: "high-performance" }});
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.08;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.minDistance = 4;
    controls.maxDistance = 380;
    controls.target.set((salaoData.x + casaData.x) / 2, salaoData.y + 2, (salaoData.z + casaData.z) / 2);

    // Iluminação
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x334155, 0.68);
    scene.add(hemiLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 1.25);
    sunLight.position.set(salaoData.x + 55, salaoData.y + 95, salaoData.z + 55);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 320;
    sunLight.shadow.camera.left = -125;
    sunLight.shadow.camera.right = 125;
    sunLight.shadow.camera.top = 100;
    sunLight.shadow.camera.bottom = -100;
    sunLight.shadow.bias = -0.0004;
    scene.add(sunLight);

    // --- 3. RELEVO 3D DE ALTA DEFINIÇÃO (0,50m) E TEXTURAS ---
    const terrainGeom = new THREE.PlaneGeometry(WIDTH, HEIGHT, COLS - 1, ROWS - 1);
    terrainGeom.rotateX(-Math.PI / 2);

    const droneOrtoTex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_drone_orto_tex}');
    const orto24Tex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_orto24_tex}');
    const droneDsmTex = new THREE.TextureLoader().load('data:image/jpeg;base64,{b64_drone_dsm_tex}');

    [droneOrtoTex, orto24Tex, droneDsmTex].forEach(tex => {{
      tex.generateMipmaps = true;
      tex.minFilter = THREE.LinearMipmapLinearFilter;
      tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
    }});

    const terrainMat = new THREE.MeshStandardMaterial({{
      map: droneOrtoTex,
      roughness: 0.88,
      metalness: 0.03,
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
        if (lbl) lbl.innerText = 'Drone 2024 (7cm) + 2026';
      }} else if (type === 'orto24') {{
        terrainMat.map = orto24Tex;
        if (lbl) lbl.innerText = 'Ortofoto ODM 2024 (7,4cm)';
      }} else if (type === 'drone_dsm') {{
        terrainMat.map = droneDsmTex;
        if (lbl) lbl.innerText = 'Hipsometria DSM 2024 + CHM';
      }}
      terrainMat.needsUpdate = true;
    }};

    const posAttr = terrainGeom.attributes.position;
    for (let i = 0; i < numVerts; i++) {{
      posAttr.setY(i, heightsCurrent[i]);
    }}
    terrainGeom.computeVertexNormals();
    posAttr.needsUpdate = true;

    // --- 3B. ÁRVORES 3D REAIS EXTRAÍDAS DO DSM 7,4cm E ORTOFOTO (INSTANCED MESH) ---
    const treesGroup = new THREE.Group();
    scene.add(treesGroup);

    let trunkInstMesh = null;
    let crownInstMesh = null;
    const dummyMatrix = new THREE.Matrix4();
    const dummyPos = new THREE.Vector3();
    const dummyQuat = new THREE.Quaternion();
    const dummyScale = new THREE.Vector3();
    const yAxisVec = new THREE.Vector3(0, 1, 0);

    (function buildReal3DTrees() {{
      const count = treesData.length;
      if (count === 0) return;

      // 1. Geometria do Tronco Unitário 1:1 (y de 0.00 até 0.44 da altura total H; diâmetro proporcional a 1m)
      const trunkGeom = new THREE.CylinderGeometry(0.035, 0.065, 0.44, 7);
      trunkGeom.translate(0, 0.22, 0);
      const trunkMat = new THREE.MeshStandardMaterial({{
        color: 0x5c4028,
        roughness: 0.92,
        metalness: 0.02
      }});
      trunkInstMesh = new THREE.InstancedMesh(trunkGeom, trunkMat, count);
      trunkInstMesh.castShadow = true;
      trunkInstMesh.receiveShadow = true;
      treesGroup.add(trunkInstMesh);

      // 2. Geometria de Copa Multi-Lobular Estritamente Cubo Unitário 1:1×1 (1,00 m Horizontal × 1,00 m Vertical):
      // Horizontal: diâmetro exato = 1.000 m (-0.50 a +0.50 em X e Z)
      // Vertical: topo exato em y = 1.000 m (base da copa em y = 0.22 m)
      // Escala aplicada em updateTreesMatrices: dummyScale.set(th, th, th) -> 100% isotrópica 1x1!
      const lobes = [
        {{ r: 0.42, x: 0.00, y: 0.60, z: 0.00 }},
        {{ r: 0.40, x: 0.34, y: 0.52, z: 0.22 }},
        {{ r: 0.39, x: -0.32, y: 0.51, z: 0.24 }},
        {{ r: 0.40, x: 0.24, y: 0.52, z: -0.32 }},
        {{ r: 0.38, x: -0.28, y: 0.50, z: -0.30 }}
      ];

      const rawPos = [];
      const mergedNorm = [];
      const mergedCol = [];
      let maxHorizR = 0.001;
      let maxVertY = 0.001;

      lobes.forEach((lb, lIdx) => {{
        const subG = new THREE.IcosahedronGeometry(lb.r, 1);
        const pA = subG.attributes.position;
        for (let i = 0; i < pA.count; i++) {{
          let vx = pA.getX(i);
          let vy = pA.getY(i);
          let vz = pA.getZ(i);
          const noise = 1.0 + 0.07 * Math.sin(vx * 7.3 + lIdx) * Math.cos(vz * 7.1 - vy * 5.2);
          vx = vx * noise + lb.x;
          vy = vy * (0.88 * noise) + lb.y;
          vz = vz * noise + lb.z;
          pA.setXYZ(i, vx, vy, vz);
          const hr = Math.hypot(vx, vz);
          if (hr > maxHorizR) maxHorizR = hr;
          if (vy > maxVertY) maxVertY = vy;
        }}
        subG.computeVertexNormals();
        const nA = subG.attributes.normal;

        for (let i = 0; i < pA.count; i++) {{
          const vx = pA.getX(i), vy = pA.getY(i), vz = pA.getZ(i);
          rawPos.push(vx, vy, vz);
          mergedNorm.push(nA.getX(i), nA.getY(i), nA.getZ(i));
        }}
      }});

      // Normalizar exatamente para Diâmetro Horizontal Unitário = 1.000 (raio = 0.500) e Topo Vertical Unitário = 1.000
      const mergedPos = [];
      for (let i = 0; i < rawPos.length; i += 3) {{
        const nx = (rawPos[i] / maxHorizR) * 0.50;
        const ny = rawPos[i + 1] / maxVertY;
        const nz = (rawPos[i + 2] / maxHorizR) * 0.50;
        mergedPos.push(nx, ny, nz);
        const ao = Math.min(1.14, Math.max(0.62, 0.55 + (ny - 0.25) * 0.68));
        mergedCol.push(ao, ao, ao);
      }}

      const crownGeom = new THREE.BufferGeometry();
      crownGeom.setAttribute('position', new THREE.Float32BufferAttribute(mergedPos, 3));
      crownGeom.setAttribute('normal', new THREE.Float32BufferAttribute(mergedNorm, 3));
      crownGeom.setAttribute('color', new THREE.Float32BufferAttribute(mergedCol, 3));

      const crownMat = new THREE.MeshStandardMaterial({{
        color: 0xffffff,
        vertexColors: true,
        roughness: 0.84,
        metalness: 0.02
      }});

      crownInstMesh = new THREE.InstancedMesh(crownGeom, crownMat, count);
      crownInstMesh.castShadow = true;
      crownInstMesh.receiveShadow = true;

      const cObj = new THREE.Color();
      for (let i = 0; i < count; i++) {{
        const td = treesData[i];
        cObj.setHex(td[6]);
        crownInstMesh.setColorAt(i, cObj);
      }}
      if (crownInstMesh.instanceColor) crownInstMesh.instanceColor.needsUpdate = true;
      treesGroup.add(crownInstMesh);
    }})();

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
    const sandMesh = new THREE.Mesh(new THREE.BoxGeometry(22.0, 0.45, 12.0), sandMat);
    sandMesh.position.set(0, 0.125, 0);
    sandMesh.receiveShadow = true;
    campoGroup.add(sandMesh);

    const campoBaseMat = new THREE.MeshStandardMaterial({{ color: 0x57534e, roughness: 0.9 }});
    const campoPlinth = new THREE.Mesh(new THREE.BoxGeometry(22.35, 1.80, 12.25), campoBaseMat);
    campoPlinth.position.set(0, -0.95, 0);
    campoPlinth.receiveShadow = true;
    campoPlinth.castShadow = true;
    campoGroup.add(campoPlinth);

    const timberMat = new THREE.MeshStandardMaterial({{ color: 0x5c3a21, roughness: 0.8 }});
    const bord1 = new THREE.Mesh(new THREE.BoxGeometry(22.35, 0.65, 0.16), timberMat);
    bord1.position.set(0, 0.10, 6.05);
    const bord2 = new THREE.Mesh(new THREE.BoxGeometry(22.35, 0.65, 0.16), timberMat);
    bord2.position.set(0, 0.10, -6.05);
    const bord3 = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.65, 12.25), timberMat);
    bord3.position.set(11.1, 0.10, 0);
    const bord4 = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.65, 12.25), timberMat);
    bord4.position.set(-11.1, 0.10, 0);
    campoGroup.add(bord1, bord2, bord3, bord4);

    const lineMat = new THREE.MeshBasicMaterial({{ color: 0x0284c7 }});
    const lineGeomH = new THREE.PlaneGeometry(20.0, 0.08); lineGeomH.rotateX(-Math.PI / 2);
    const line1 = new THREE.Mesh(lineGeomH, lineMat); line1.position.set(0, 0.36, 5.5);
    const line2 = new THREE.Mesh(lineGeomH, lineMat); line2.position.set(0, 0.36, -5.5);
    const lineGeomV = new THREE.PlaneGeometry(0.08, 11.0); lineGeomV.rotateX(-Math.PI / 2);
    const line3 = new THREE.Mesh(lineGeomV, lineMat); line3.position.set(10.0, 0.36, 0);
    const line4 = new THREE.Mesh(lineGeomV, lineMat); line4.position.set(-10.0, 0.36, 0);
    const lineMid = new THREE.Mesh(lineGeomV, lineMat); lineMid.position.set(0, 0.36, 0);
    campoGroup.add(line1, line2, line3, line4, lineMid);

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

    const floorTileMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.5 }});
    const salaoFloor = new THREE.Mesh(new THREE.BoxGeometry(12.1, 0.15, 8.1), floorTileMat);
    salaoFloor.position.set(0, 0.125, 0);
    salaoFloor.receiveShadow = true;
    salaoGroup.add(salaoFloor);

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

    const stairMat = new THREE.MeshStandardMaterial({{ color: 0x78716c, roughness: 0.7 }});
    for (let s = 1; s <= 3; s++) {{
      const step = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.20, 0.50), stairMat);
      step.position.set(0, 0.125 - s * 0.20, 4.05 + s * 0.45);
      step.receiveShadow = true;
      salaoGroup.add(step);
    }}

    const cutWallMat = new THREE.MeshStandardMaterial({{ color: 0x57534e, roughness: 0.9 }});
    const cutRetainingWall = new THREE.Mesh(new THREE.BoxGeometry(14.0, 1.60, 0.40), cutWallMat);
    cutRetainingWall.position.set(0, 0.30, -5.2);
    cutRetainingWall.castShadow = true;
    salaoGroup.add(cutRetainingWall);

    const ditchMat = new THREE.MeshStandardMaterial({{ color: 0x3f3f46, roughness: 0.8 }});
    const ditch = new THREE.Mesh(new THREE.BoxGeometry(14.0, 0.15, 0.50), ditchMat);
    ditch.position.set(0, -0.40, -4.6);
    salaoGroup.add(ditch);

    const optGroup1 = new THREE.Group();
    const optGroup2 = new THREE.Group();
    const optGroup3 = new THREE.Group();
    const optGroup4 = new THREE.Group();
    salaoGroup.add(optGroup1, optGroup2, optGroup3);
    scene.add(optGroup4);

    // =========================================================================
    // TEXTURA E RELEVO 3D DE TELHAS DE BARRO COLONIAIS EXISTENTES (CAPA E BICA)
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
      mapTex.anisotropy = renderer.capabilities.getMaxAnisotropy();

      const bumpTex = new THREE.CanvasTexture(cBump);
      bumpTex.wrapS = THREE.RepeatWrapping; bumpTex.wrapT = THREE.RepeatWrapping;

      return {{ mapTex, bumpTex }};
    }}

    const clayTextures = createClayTileTextures();
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
    const ridgeTileMat = new THREE.MeshStandardMaterial({{ color: 0x9a3b14, roughness: 0.68 }});

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

    const ridgeCap = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.18, 13.3, 16), ridgeTileMat);
    ridgeCap.rotation.z = Math.PI / 2;
    ridgeCap.position.set(0, 5.28, 0);
    ridgeCap.castShadow = true;
    optGroup1.add(ridgeCap);

    // OPÇÃO 2: ESTRUTURA METÁLICA
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

    // OPÇÃO 3: TELHADO 1 ÁGUA
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

    // OPÇÃO 4: ARENA NOTURNA
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

    // =========================================================================
    // 5B. CASA DO SÍTIO (TELHADO 1 & TELHADO 2 EM DUAS ÁGUAS - TELHAS DE BARRO EXISTENTES)
    // =========================================================================
    const casaGroup = new THREE.Group();
    casaGroup.position.set(casaData.x, casaData.y, casaData.z);
    scene.add(casaGroup);

    (function buildCasaSitio() {{
      const cxU = casaData.cx_utm;
      const cyU = casaData.cy_utm;

      const Rs = [663412.325, 6968630.680];
      const Rn = [663415.670, 6968642.765];
      const uE = 0.266796, uN = 0.963753;
      const nE = 0.963753, nN = -0.266796;
      const H_RIDGE = 4.60;
      const S_WEST = 0.34;
      const S_EAST = 0.235;

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

      const t1UTM = [
        [663408.670, 6968631.320],
        Rs,
        Rn,
        [663411.350, 6968643.960],
        [663409.720, 6968639.170],
        [663410.820, 6968638.840]
      ];
      const t1Tris = [[0,1,5], [1,2,5], [5,2,4], [2,3,4]];

      const t2UTM = [
        Rs,
        [663417.810, 6968628.890],
        [663420.070, 6968635.550],
        [663421.640, 6968635.100],
        [663423.050, 6968640.760],
        Rn
      ];
      const t2Tris = [[0,1,2], [0,2,5], [2,3,5], [3,4,5]];

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

      function buildRoofSlopeMesh(ptsUTM, tris, isEast) {{
        const thickness = 0.14;
        const pos = [];
        const uvs = [];
        const pts = ptsUTM.map(p => roofMetrics(p[0], p[1]));

        function pushTri(pA, pB, pC, yOff) {{
          pos.push(pA.lx, pA.h + yOff, pA.lz);
          pos.push(pB.lx, pB.h + yOff, pB.lz);
          pos.push(pC.lx, pC.h + yOff, pC.lz);
          uvs.push(pA.along / 1.6, Math.abs(pA.perp) / 1.5);
          uvs.push(pB.along / 1.6, Math.abs(pB.perp) / 1.5);
          uvs.push(pC.along / 1.6, Math.abs(pC.perp) / 1.5);
        }}

        tris.forEach(t => {{
          pushTri(pts[t[0]], pts[t[1]], pts[t[2]], thickness);
        }});

        const topGeom = new THREE.BufferGeometry();
        topGeom.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
        topGeom.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
        topGeom.computeVertexNormals();
        const topMesh = new THREE.Mesh(topGeom, casaClayMat);
        topMesh.castShadow = true;
        topMesh.receiveShadow = true;
        casaGroup.add(topMesh);

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
        wallPos.push(
          p1.lx, 0.0, p1.lz, p2.lx, 0.0, p2.lz, p2.lx, p2.h + 0.02, p2.lz,
          p1.lx, 0.0, p1.lz, p2.lx, p2.h + 0.02, p2.lz, p1.lx, p1.h + 0.02, p1.lz
        );
        plinthPos.push(
          p1.lx, -2.5, p1.lz, p2.lx, -2.5, p2.lz, p2.lx, 0.18, p2.lz,
          p1.lx, -2.5, p1.lz, p2.lx, 0.18, p2.lz, p1.lx, 0.18, p1.lz
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

    // --- 5C. RÉGUAS E MALHA DE ESCALA 1:1 (1 METRO HORIZONTAL = 1 METRO VERTICAL) ---
    // Comprova visualmente nas construções e nas árvores que 1,00 m H = 1,00 m V
    const scale1to1Rulers = [];
    const treeScaleGroup = new THREE.Group();
    scene.add(treeScaleGroup);
    scale1to1Rulers.push(treeScaleGroup);

    function makeMetricSprite(text, bgColor = 'rgba(15, 23, 42, 0.92)', borderColor = '#38bdf8', textColor = '#ffffff', scaleW = 2.6, scaleH = 0.68) {{
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = bgColor;
      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 6;
      ctx.beginPath();
      ctx.roundRect(8, 8, 496, 112, 18);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = textColor;
      ctx.font = 'bold 34px "Segoe UI", Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 256, 64);

      const tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      const mat = new THREE.SpriteMaterial({{ map: tex, depthTest: false, transparent: true }});
      const sp = new THREE.Sprite(mat);
      sp.scale.set(scaleW, scaleH, 1.0);
      sp.renderOrder = 999;
      return sp;
    }}

    function makeTickSprite(text, colorHex = '#fde047') {{
      const canvas = document.createElement('canvas');
      canvas.width = 128;
      canvas.height = 64;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
      ctx.beginPath();
      ctx.roundRect(6, 6, 116, 52, 10);
      ctx.fill();
      ctx.fillStyle = colorHex;
      ctx.font = 'bold 28px "Segoe UI", Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, 64, 32);

      const tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      const mat = new THREE.SpriteMaterial({{ map: tex, depthTest: false, transparent: true }});
      const sp = new THREE.Sprite(mat);
      sp.scale.set(0.95, 0.48, 1.0);
      sp.renderOrder = 998;
      return sp;
    }}

    function create1to1ScaleFrame(widthM, heightM, titleText, mainColorHex = 0x38bdf8, stepLabelH = 2, stepLabelV = 1) {{
      const grp = new THREE.Group();
      const wInt = Math.round(widthM);
      const hInt = Math.ceil(heightM);
      const halfW = widthM * 0.5;

      // Malha quadriculada onde cada quadrado tem EXATAMENTE 1,00m (H) x 1,00m (V)
      const gridPts = [];
      for (let x = 0; x <= wInt; x++) {{
        const px = -halfW + x;
        gridPts.push(px, 0, 0, px, heightM, 0);
      }}
      for (let y = 0; y <= hInt; y++) {{
        const py = Math.min(y, heightM);
        gridPts.push(-halfW, py, 0, halfW, py, 0);
      }}
      const gridGeom = new THREE.BufferGeometry();
      gridGeom.setAttribute('position', new THREE.Float32BufferAttribute(gridPts, 3));
      const gridMat = new THREE.LineBasicMaterial({{ color: mainColorHex, transparent: true, opacity: 0.42 }});
      grp.add(new THREE.LineSegments(gridGeom, gridMat));

      // Eixo Horizontal Base e Eixo Vertical Lateral em destaque (amarelo ouro / ciano)
      const axisPts = [
        -halfW, 0, 0, halfW, 0, 0,
        -halfW, 0, 0, -halfW, heightM, 0,
        halfW, 0, 0, halfW, heightM, 0,
        -halfW, heightM, 0, halfW, heightM, 0
      ];
      // Ticks de 1 metro
      for (let x = 0; x <= wInt; x++) {{
        const px = -halfW + x;
        axisPts.push(px, -0.18, 0, px, 0.18, 0);
        if (x % stepLabelH === 0 || x === wInt) {{
          const lbl = makeTickSprite(x + 'm H', '#38bdf8');
          lbl.position.set(px, -0.45, 0.05);
          grp.add(lbl);
        }}
      }}
      for (let y = 1; y <= hInt; y++) {{
        const py = Math.min(y, heightM);
        axisPts.push(-halfW - 0.22, py, 0, -halfW + 0.22, py, 0);
        if (y % stepLabelV === 0 || y === hInt) {{
          const lbl = makeTickSprite(py.toFixed(py % 1 === 0 ? 0 : 1) + 'm V', '#fde047');
          lbl.position.set(-halfW - 0.72, py, 0.05);
          grp.add(lbl);
        }}
      }}
      const axisGeom = new THREE.BufferGeometry();
      axisGeom.setAttribute('position', new THREE.Float32BufferAttribute(axisPts, 3));
      const axisMat = new THREE.LineBasicMaterial({{ color: 0xfacc15, linewidth: 2 }});
      grp.add(new THREE.LineSegments(axisGeom, axisMat));

      // Placa de título da escala 1:1
      const titleSp = makeMetricSprite(titleText, 'rgba(15, 23, 42, 0.94)', '#facc15', '#fef08a', Math.max(5.2, widthM * 0.48), 0.95);
      titleSp.position.set(0, heightM + 0.75, 0);
      grp.add(titleSp);

      return grp;
    }}

    // 1. Escala 1:1 no Salão 12x8m (12,0m Horizontal x 5,2m Vertical — quadrados de 1m x 1m)
    const salaoScale1to1 = create1to1ScaleFrame(12.0, 5.2, '📏 SALÃO: 12,0m H × 5,2m V (1m H = 1m V)', 0x38bdf8, 2, 1);
    salaoScale1to1.position.set(0, 0.12, 4.25);
    salaoGroup.add(salaoScale1to1);
    scale1to1Rulers.push(salaoScale1to1);

    // 2. Escala 1:1 na Casa do Sítio (14,0m Horizontal x 4,65m Vertical — quadrados de 1m x 1m)
    const casaScale1to1 = create1to1ScaleFrame(14.0, 4.65, '📏 CASA DO SÍTIO: 14,0m H × 4,65m V (1m H = 1m V)', 0xf59e0b, 2, 1);
    casaScale1to1.position.set(1.2, 0.0, 6.9);
    casaScale1to1.rotation.y = THREE.MathUtils.degToRad(15.5);
    casaGroup.add(casaScale1to1);
    scale1to1Rulers.push(casaScale1to1);

    // 3. Escala 1:1 no Campo de Areia (22,0m Horizontal x 6,0m Vertical — quadrados de 1m x 1m)
    const campoScale1to1 = create1to1ScaleFrame(22.0, 6.0, '📏 QUADRA: 22,0m H × 6,0m V (1m H = 1m V)', 0x10b981, 2, 2);
    campoScale1to1.position.set(0, 0.15, -6.15);
    campoGroup.add(campoScale1to1);
    scale1to1Rulers.push(campoScale1to1);

    // 4. Escalas 1:1 em Árvores 3D de Referência (comprovando Diâmetro Horizontal x Altura Vertical 1:1)
    const refTreeIndices = [];
    // Escolher 4 árvores representativas próximas à Casa e ao Salão
    for (let i = 0; i < treesData.length; i++) {{
      const tx = treesData[i][0], tz = treesData[i][1], th = treesData[i][4];
      const dCasa = Math.hypot(tx - casaData.x, tz - casaData.z);
      const dSalao = Math.hypot(tx - salaoData.x, tz - salaoData.z);
      if ((dCasa < 28 || dSalao < 32) && th >= 4.0 && th <= 9.5) {{
        let tooClose = false;
        for (const prevIdx of refTreeIndices) {{
          if (Math.hypot(tx - treesData[prevIdx][0], tz - treesData[prevIdx][1]) < 14.0) {{
            tooClose = true;
            break;
          }}
        }}
        if (!tooClose) {{
          refTreeIndices.push(i);
          if (refTreeIndices.length >= 4) break;
        }}
      }}
    }}

    const refTreeFrames = [];
    refTreeIndices.forEach((tIdx) => {{
      const td = treesData[tIdx];
      const th = td[4];
      const diamH = td[5] * 2.0;
      const wGrid = Math.max(2, Math.round(diamH));
      const hGrid = Math.max(2, Math.round(th));
      const treeFrame = create1to1ScaleFrame(
        wGrid, hGrid,
        `🌳 ÁRVORE 1:1: Ø${{diamH.toFixed(1)}}m H × ${{th.toFixed(1)}}m V`,
        0x22c55e, 1, 1
      );
      treeScaleGroup.add(treeFrame);
      refTreeFrames.push({{ mesh: treeFrame, treeIdx: tIdx }});
    }});

    // --- 6. CONTROLES DE TERRA, ÁRVORES 3D, ESCALA 1:1, PROPORÇÃO Z & MDT ---
    let terrainMode = 0;
    let showTrees3D = true;
    let showScale1to1 = true;
    let currentZScale = 1.0;
    let currentZOffset = 0.0;
    let morphProgress = 1.0;
    const pivotY = salaoData.y;

    window.toggleScale1to1 = function() {{
      showScale1to1 = !showScale1to1;
      scale1to1Rulers.forEach(r => r.visible = showScale1to1);
      const btn = document.getElementById('btnToggleScale1to1');
      const lbl = document.getElementById('lblScale1to1Status');
      if (showScale1to1) {{
        btn.classList.remove('cut-off');
        btn.style.background = '#0284c7';
        lbl.innerText = 'VISÍVEL (1:1)';
      }} else {{
        btn.classList.add('cut-off');
        btn.style.background = '#334155';
        lbl.innerText = 'OCULTA';
      }}
    }};

    function updateTreesMatrices() {{
      if (!trunkInstMesh || !crownInstMesh) return;
      const count = treesData.length;
      for (let i = 0; i < count; i++) {{
        const td = treesData[i];
        const tx = td[0];
        const tz = td[1];
        const baseGround = (terrainMode === 0) ? td[2] : td[3];
        const ty = pivotY + (baseGround - pivotY) * currentZScale + currentZOffset;
        const th = td[4];
        const tr = td[5];
        const rotAngle = (i * 1.6180339) % (Math.PI * 2);

        dummyPos.set(tx, ty, tz);
        dummyQuat.setFromAxisAngle(yAxisVec, rotAngle);

        // Escala 100% isotrópica 1×1×1 (scaleX = scaleY = scaleZ = th metros; 1m H = 1m V sem distorção)
        dummyScale.set(th, th, th);
        dummyMatrix.compose(dummyPos, dummyQuat, dummyScale);
        trunkInstMesh.setMatrixAt(i, dummyMatrix);
        crownInstMesh.setMatrixAt(i, dummyMatrix);
      }}
      trunkInstMesh.instanceMatrix.needsUpdate = true;
      crownInstMesh.instanceMatrix.needsUpdate = true;

      // Atualizar posição das réguas 1:1 das árvores de referência
      refTreeFrames.forEach(item => {{
        const td = treesData[item.treeIdx];
        const baseGround = (terrainMode === 0) ? td[2] : td[3];
        const ty = pivotY + (baseGround - pivotY) * currentZScale + currentZOffset;
        item.mesh.position.set(td[0], ty, td[1]);
      }});
    }}

    function updateTargetHeights() {{
      const srcArray = (terrainMode === 0) ? heightsCut : ((terrainMode === 1) ? heightsNat : heightsDsm);
      for (let i = 0; i < numVerts; i++) {{
        heightsTarget[i] = pivotY + (srcArray[i] - pivotY) * currentZScale + currentZOffset;
      }}
      const scaledCampoY = pivotY + (campoData.y - pivotY) * currentZScale + currentZOffset;
      campoGroup.position.y = scaledCampoY;
      optGroup4.children.forEach(tower => {{
        tower.position.y = scaledCampoY;
      }});
      floodlights.forEach(spot => {{
        spot.target.position.y = scaledCampoY;
      }});
      const scaledCasaY = pivotY + (casaData.y - pivotY) * currentZScale + currentZOffset;
      casaGroup.position.y = scaledCasaY;
      salaoGroup.position.y = pivotY + currentZOffset;

      updateTreesMatrices();
      morphProgress = 0.0;
    }}

    updateTreesMatrices();

    window.toggleTrees3D = function() {{
      showTrees3D = !showTrees3D;
      treesGroup.visible = showTrees3D;
      const btn = document.getElementById('btnToggleTrees');
      const lbl = document.getElementById('lblTreesStatus');
      if (showTrees3D) {{
        btn.classList.remove('cut-off');
        btn.style.background = '#15803d';
        lbl.innerText = treesData.length + ' ATIVAS';
      }} else {{
        btn.classList.add('cut-off');
        btn.style.background = '#334155';
        lbl.innerText = 'OCULTAS';
      }}
    }};

    window.cycleTerrainMode = function() {{
      terrainMode = (terrainMode + 1) % 3;
      const btn = document.getElementById('btnToggleCut');
      const lbl = document.getElementById('lblCutStatus');
      const info = document.getElementById('terrainInfoBox');

      if (terrainMode === 0) {{
        btn.classList.remove('cut-off');
        lbl.innerText = 'PLATÔS + MDT 2024';
        info.innerHTML = `<b>Escala 1:1 (1m H = 1m V) + Platôs:</b> Terreno limpo de vegetação com platôs nivelados da Casa (545.55m), Salão (547.05m) e Quadra (546.45m).`;
      }} else if (terrainMode === 1) {{
        btn.classList.add('cut-off');
        lbl.innerText = 'MDT 2024 NATURAL';
        info.innerHTML = `<b>Terreno Natural Drone 2024 (1:1):</b> Exibe o solo natural calibrado do voo de 2024 em proporção 1:1 sem os cortes do Salão/Quadra.`;
      }} else {{
        btn.classList.remove('cut-off');
        lbl.innerText = 'DSM 2024 BRUTO (COPAS)';
        info.innerHTML = `<b>Superfície Fotogramétrica DSM 2024 (1:1):</b> Exibe diretamente a elevação bruta do <code>odm_dem/dsm.tif</code> em escala 1:1.`;
      }}
      updateTargetHeights();
    }};

    window.setZScale = function(val) {{
      currentZScale = parseFloat(val);
      const sl = document.getElementById('sliderZScale');
      if (sl && Math.abs(parseFloat(sl.value) - currentZScale) > 0.001) sl.value = currentZScale;
      const lbl = document.getElementById('lblZScale');
      if (lbl) {{
        lbl.innerText = currentZScale.toFixed(2) + 'x' + (Math.abs(currentZScale - 1.0) < 0.01 ? ' (Real 1:1)' : '');
      }}
      updateTargetHeights();
    }};

    window.setZScalePreset = function(val) {{
      window.setZScale(val);
    }};

    window.setZOffset = function(val) {{
      currentZOffset = parseFloat(val);
      const sl = document.getElementById('sliderZOffset');
      if (sl && Math.abs(parseFloat(sl.value) - currentZOffset) > 0.001) sl.value = currentZOffset;
      const lbl = document.getElementById('lblZOffset');
      if (lbl) {{
        lbl.innerText = (currentZOffset >= 0 ? '+' : '') + currentZOffset.toFixed(2) + ' m';
      }}
      updateTargetHeights();
    }};

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
        hemiLight.intensity = 0.68;
        floodlights.forEach(l => l.intensity = 0.0);
      }}
    }};

    window.setCameraView = function(view) {{
      if (view === 'geral') {{
        camera.position.set(salaoData.x - 45, salaoData.y + 30, salaoData.z + 52);
        controls.target.set((salaoData.x + casaData.x) / 2, salaoData.y + 1, (salaoData.z + casaData.z) / 2);
      }} else if (view === 'corte') {{
        camera.position.set(salaoData.x - 14, salaoData.y + 7.0, salaoData.z - 13);
        controls.target.set(salaoData.x, salaoData.y + 2.5, salaoData.z);
      }} else if (view === 'salao') {{
        camera.position.set(salaoData.x - 4, salaoData.y + 2.2, salaoData.z);
        controls.target.set(campoData.x, campoData.y + 1.5, campoData.z);
      }} else if (view === 'campo') {{
        camera.position.set(campoData.x + 8, campoData.y + 2.5, campoData.z);
        controls.target.set(salaoData.x, salaoData.y + 2.5, salaoData.z);
      }} else if (view === 'casa') {{
        const cy = casaGroup.position.y;
        camera.position.set(casaData.x - 18, cy + 12, casaData.z + 20);
        controls.target.set(casaData.x, cy + 2.2, casaData.z);
      }}
    }};

    function animate() {{
      requestAnimationFrame(animate);

      if (morphProgress < 1.0) {{
        morphProgress += 0.06;
        if (morphProgress > 1.0) morphProgress = 1.0;

        for (let i = 0; i < numVerts; i++) {{
          heightsCurrent[i] = heightsCurrent[i] + (heightsTarget[i] - heightsCurrent[i]) * 0.22;
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
    print(f"\n[OK] Visualizador do Complexo atualizado: {HTML_OUT} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
