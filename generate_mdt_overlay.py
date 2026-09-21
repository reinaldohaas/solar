import rasterio
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import zipfile
import io

src_path = r'C:\Users\haas\github\solar\MDT_Novo_sitio_das_andorinhas_WGS84.tif'
kmz_out = r'C:\Users\haas\github\solar\MDT_Hipsometria_Overlay.kmz'

with rasterio.open(src_path) as src:
    elev = src.read(1)
    nodata = src.nodata
    bounds = src.bounds # west, south, east, north

mask = (elev != nodata) & (~np.isnan(elev))
min_val = np.min(elev[mask])
max_val = np.max(elev[mask])

# Normalize 0 to 1
norm = (elev - min_val) / (max_val - min_val)
norm = np.clip(norm, 0, 1)

# Apply colormap
cmap = plt.get_cmap('terrain')
rgba = cmap(norm)

# Set alpha to 0 for nodata, and 0.55 for valid data
rgba[..., 3] = np.where(mask, 0.60, 0.0)

img_data = (rgba * 255).astype(np.uint8)
img = Image.fromarray(img_data, mode='RGBA')

img_byte_arr = io.BytesIO()
img.save(img_byte_arr, format='PNG')
img_bytes = img_byte_arr.getvalue()

kml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Hipsometria MDT 1m - Sitio das Andorinhas</name>
    <GroundOverlay>
      <name>MDT 1m Elevação ({min_val:.0f}m - {max_val:.0f}m)</name>
      <Icon>
        <href>overlay.png</href>
      </Icon>
      <LatLonBox>
        <north>{bounds.top:.7f}</north>
        <south>{bounds.bottom:.7f}</south>
        <east>{bounds.right:.7f}</east>
        <west>{bounds.left:.7f}</west>
      </LatLonBox>
    </GroundOverlay>
  </Document>
</kml>
"""

with zipfile.ZipFile(kmz_out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('doc.kml', kml_content.encode('utf-8'))
    z.writestr('overlay.png', img_bytes)

print(f"Success: Created {kmz_out} with bounds {bounds}")
