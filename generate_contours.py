import rasterio
import numpy as np
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from pyproj import Transformer
import zipfile
import os

tif_path = r'C:\Users\haas\github\solar\MDT_Novo_sitio_das_andorinhas.tif'
with rasterio.open(tif_path) as src:
    elev = src.read(1)
    nodata = src.nodata
    transform = src.transform
    crs = src.crs

elev_clean = np.where(elev == nodata, np.nan, elev)
min_elev = int(np.floor(np.nanmin(elev_clean)))
max_elev = int(np.ceil(np.nanmax(elev_clean)))

# 5m contour intervals
levels_5m = np.arange(min_elev // 5 * 5, (max_elev // 5 + 1) * 5 + 5, 5)

fig, ax = plt.subplots()
cs = ax.contour(elev_clean, levels=levels_5m)
plt.close(fig)

transformer = Transformer.from_crs('EPSG:31982', 'EPSG:4326', always_xy=True)

kml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<kml xmlns="http://www.opengis.net/kml/2.2">',
    '<Document>',
    '  <name>Curvas de Nivel (MDT 1m) - Sitio das Andorinhas</name>',
    '  <Style id="contour_major">',
    '    <LineStyle><color>ff1040c0</color><width>2.2</width></LineStyle>',
    '  </Style>',
    '  <Style id="contour_minor">',
    '    <LineStyle><color>993070d0</color><width>1.2</width></LineStyle>',
    '  </Style>'
]

count = 0
for level, segs in zip(cs.levels, cs.allsegs):
    is_major = (level % 25 == 0)
    style = '#contour_major' if is_major else '#contour_minor'
    for seg in segs:
        if len(seg) >= 2:
            xs, ys = rasterio.transform.xy(transform, seg[:, 1], seg[:, 0])
            lons, lats = transformer.transform(xs, ys)
            coords_str = ' '.join([f'{lon:.7f},{lat:.7f},{level:.1f}' for lon, lat in zip(lons, lats)])
            kml_lines.append('  <Placemark>')
            kml_lines.append(f'    <name>{level:.0f} m</name>')
            kml_lines.append(f'    <styleUrl>{style}</styleUrl>')
            kml_lines.append('    <LineString>')
            kml_lines.append('      <tessellate>1</tessellate>')
            kml_lines.append('      <altitudeMode>clampToGround</altitudeMode>')
            kml_lines.append(f'      <coordinates>{coords_str}</coordinates>')
            kml_lines.append('    </LineString>')
            kml_lines.append('  </Placemark>')
            count += 1

kml_lines.append('</Document>')
kml_lines.append('</kml>')

kml_content = '\n'.join(kml_lines)
kmz_out = r'C:\Users\haas\github\solar\MDT_Curvas_de_Nivel.kmz'
with zipfile.ZipFile(kmz_out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('doc.kml', kml_content.encode('utf-8'))

print(f'Success: Generated {count} contour lines in {kmz_out}')
