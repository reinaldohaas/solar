import glob
import os
import re
import numpy as np
from PIL import Image
from pyproj import Transformer
import rasterio
from rasterio.transform import from_bounds

SOLAR_DIR = r"C:\Users\haas\github\solar"
EXTRACT_DIR = os.path.join(SOLAR_DIR, "Estrada-Ribeiro-dos-Ovos-01-03-2026-dsm_extraido", "4")
OUT_DSM_FULL = os.path.join(SOLAR_DIR, "DSM_Drone_2026_Completo.tif")
OUT_DSM_COMPLEX = os.path.join(SOLAR_DIR, "DSM_Drone_2026_Complexo.tif")

def main():
    print("=== COSTURANDO TILES DO DSM DRONE 2026 (PRECISÃO GEOGRÁFICA) ===")
    kml_files = glob.glob(os.path.join(EXTRACT_DIR, "*", "*.kml"))
    print(f"Total de tiles encontrados: {len(kml_files)}")

    t_wgs_to_utm = Transformer.from_crs("EPSG:4326", "EPSG:31982", always_xy=True)

    tiles = []
    for kf in kml_files:
        with open(kf, "r", encoding="utf-8") as f:
            c = f.read()
        n = float(re.search(r"<north>([^<]+)</north>", c).group(1))
        s = float(re.search(r"<south>([^<]+)</south>", c).group(1))
        e = float(re.search(r"<east>([^<]+)</east>", c).group(1))
        w = float(re.search(r"<west>([^<]+)</west>", c).group(1))

        img_p = kf.replace(".kml", ".png")
        if not os.path.exists(img_p):
            img_p = kf.replace(".kml", ".jpg")

        uw_w, uw_s = t_wgs_to_utm.transform(w, s)
        uw_e, uw_n = t_wgs_to_utm.transform(e, n)

        tiles.append({
            "img": img_p,
            "uw": uw_w, "us": uw_s, "ue": uw_e, "un": uw_n
        })

    res = 0.05 # 5 cm por pixel (resolução nativa do voo)
    min_x = min(t["uw"] for t in tiles)
    max_x = max(t["ue"] for t in tiles)
    min_y = min(t["us"] for t in tiles)
    max_y = max(t["un"] for t in tiles)

    w_px = int(np.ceil((max_x - min_x) / res))
    h_px = int(np.ceil((max_y - min_y) / res))
    print(f"Mosaico Completo: {w_px} x {h_px} px ({max_x - min_x:.1f}m x {max_y - min_y:.1f}m a {res*100:.0f}cm/px)")

    mosaic_rgba = np.zeros((4, h_px, w_px), dtype=np.uint8)

    for idx, t in enumerate(tiles):
        c0 = int(round((t["uw"] - min_x) / res))
        c1 = int(round((t["ue"] - min_x) / res))
        r0 = int(round((max_y - t["un"]) / res))
        r1 = int(round((max_y - t["us"]) / res))

        dest_w = c1 - c0
        dest_h = r1 - r0
        if dest_w <= 0 or dest_h <= 0:
            continue

        tile_img = Image.open(t["img"]).convert("RGBA")
        if tile_img.size != (dest_w, dest_h):
            tile_img = tile_img.resize((dest_w, dest_h), Image.BILINEAR)

        t_arr = np.array(tile_img)

        # Região de colagem
        r0_clip = max(0, r0)
        r1_clip = min(h_px, r1)
        c0_clip = max(0, c0)
        c1_clip = min(w_px, c1)

        src_r0 = r0_clip - r0
        src_r1 = src_r0 + (r1_clip - r0_clip)
        src_c0 = c0_clip - c0
        src_c1 = src_c0 + (c1_clip - c0_clip)

        patch = t_arr[src_r0:src_r1, src_c0:src_c1]
        alpha = patch[:, :, 3]
        mask = alpha > 0

        for b in range(4):
            curr = mosaic_rgba[b, r0_clip:r1_clip, c0_clip:c1_clip]
            curr[mask] = patch[:, :, b][mask]

        if (idx + 1) % 40 == 0 or idx == len(tiles) - 1:
            print(f"   Processados {idx + 1}/{len(tiles)} tiles...")

    transform_full = from_bounds(min_x, min_y, max_x, max_y, w_px, h_px)

    print(f"Salvando GeoTIFF Completo: {OUT_DSM_FULL}...")
    with rasterio.open(
        OUT_DSM_FULL,
        "w",
        driver="GTiff",
        height=h_px,
        width=w_px,
        count=4,
        dtype=np.uint8,
        crs="EPSG:31982",
        transform=transform_full,
        compress="lzw"
    ) as dst:
        dst.write(mosaic_rgba)

    # Recorte para o Complexo (120x100m)
    cx_complex = 663459.0
    cy_complex = 6968647.0
    half_w = 60.0
    half_h = 50.0
    box_left = cx_complex - half_w
    box_right = cx_complex + half_w
    box_bottom = cy_complex - half_h
    box_top = cy_complex + half_h

    c0 = int(round((box_left - min_x) / res))
    c1 = int(round((box_right - min_x) / res))
    r0 = int(round((max_y - box_top) / res))
    r1 = int(round((max_y - box_bottom) / res))

    crop_rgba = mosaic_rgba[:, r0:r1, c0:c1]
    ch, cw = crop_rgba.shape[1], crop_rgba.shape[2]
    transform_crop = from_bounds(box_left, box_bottom, box_right, box_top, cw, ch)

    print(f"Salvando GeoTIFF Complexo: {OUT_DSM_COMPLEX} ({cw} x {ch} px)...")
    with rasterio.open(
        OUT_DSM_COMPLEX,
        "w",
        driver="GTiff",
        height=ch,
        width=cw,
        count=4,
        dtype=np.uint8,
        crs="EPSG:31982",
        transform=transform_crop,
        compress="lzw"
    ) as dst:
        dst.write(crop_rgba)

    # Exportar também imagem RGB para visualização
    img_complex = Image.fromarray(np.transpose(crop_rgba[:3], (1, 2, 0)))
    preview_path = os.path.join(SOLAR_DIR, "preview_dsm_complexo_5cm.png")
    img_complex.save(preview_path)
    print(f"Preview salvo em: {preview_path}")

    print("=== CONCLUÍDO COM SUCESSO! ===")

if __name__ == "__main__":
    main()
