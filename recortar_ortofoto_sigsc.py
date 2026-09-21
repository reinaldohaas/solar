#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recorta a Ortofoto Oficial do SIGSC (Orto-RGB_SG-22-Z-D-I-3-SE-A.tif) para o polígono
do Novo_sitio_das_andorinhas.kmz e gera o KMZ com GroundOverlay para o Google Earth.
"""

import os
import zipfile
import xml.etree.ElementTree as ET
import rasterio
from rasterio.mask import mask
import numpy as np
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Polygon

SOLAR_DIR = r"C:\Users\haas\github\solar"
SIGSC_DIR = r"C:\Users\haas\github\SIGSC"

def main():
    kmz_path = os.path.join(SOLAR_DIR, "Novo_sitio_das_andorinhas.kmz")
    with zipfile.ZipFile(kmz_path, 'r') as z:
        for n in z.namelist():
            if n.endswith('.kml'):
                root = ET.fromstring(z.read(n))
                for c in root.iter('{http://www.opengis.net/kml/2.2}coordinates'):
                    pts = [[float(x) for x in pt.split(',')][:2] for pt in c.text.strip().split()]
                    break

    to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:31982', always_xy=True)
    to_wgs = Transformer.from_crs('EPSG:31982', 'EPSG:4326', always_xy=True)

    pts_utm = [to_utm.transform(*pt) for pt in pts]
    poly_utm = Polygon(pts_utm)
    poly_buf = poly_utm.buffer(60) # 60m de margem ao redor

    tif_in = os.path.join(SIGSC_DIR, "raster", "ortofoto_sigsc", "Orto-RGB_SG-22-Z-D-I-3-SE-A.tif")
    tif_out = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Novo_sitio_das_andorinhas.tif")

    print(f"Lendo e recortando {tif_in}...")
    with rasterio.open(tif_in) as src:
        out_img, out_transform = mask(src, [poly_buf], crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            'driver': 'GTiff',
            'height': out_img.shape[1],
            'width': out_img.shape[2],
            'transform': out_transform,
            'compress': 'deflate'
        })
        with rasterio.open(tif_out, 'w', **out_meta) as dst:
            dst.write(out_img)
        print(f"Ortofoto recortada salva: {tif_out} ({out_img.shape[2]}x{out_img.shape[1]} px)")

    # Limites WGS84 para o KMZ
    minx = out_transform[2]
    maxy = out_transform[5]
    maxx = minx + out_img.shape[2] * out_transform[0]
    miny = maxy + out_img.shape[1] * out_transform[4]

    w, s = to_wgs.transform(minx, miny)
    e, n = to_wgs.transform(maxx, maxy)

    rgb = np.transpose(out_img, (1, 2, 0))
    img_pil = Image.fromarray(rgb)
    png_path = os.path.join(SOLAR_DIR, "ortofoto_sigsc_overlay.png")
    img_pil.save(png_path, format="PNG", optimize=True)
    print(f"PNG gerado: {png_path}")

    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Folder>',
        '  <name>Ortofoto Oficial Santa Catarina - SDS/SDC (SIGSC)</name>',
        '  <GroundOverlay>',
        '    <name>Ortofoto SIGSC (Escala 1:10.000 / 0,39m)</name>',
        '    <Icon>',
        '      <href>ortofoto_sigsc_overlay.png</href>',
        '    </Icon>',
        '    <LatLonBox>',
        f'      <north>{n:.7f}</north>',
        f'      <south>{s:.7f}</south>',
        f'      <east>{e:.7f}</east>',
        f'      <west>{w:.7f}</west>',
        '    </LatLonBox>',
        '  </GroundOverlay>',
        '</Folder>',
        '</kml>'
    ]

    kmz_out = os.path.join(SOLAR_DIR, "Ortofoto_SIGSC_Sitio_das_Andorinhas.kmz")
    with zipfile.ZipFile(kmz_out, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', '\n'.join(kml_lines).encode('utf-8'))
        z.write(png_path, 'ortofoto_sigsc_overlay.png')

    print(f"KMZ da Ortofoto SIGSC gerado com sucesso: {kmz_out}")

if __name__ == '__main__':
    main()
