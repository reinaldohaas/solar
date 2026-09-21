#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Converte o MDT de 1 metro do Sítio das Andorinhas em uma Malha 3D COLLADA (.dae)
texturizada para o Google Earth Pro, exatamente como o sigsc_1m_toromodel_HD.kmz.
Isso permite substituir o relevo padrão de baixa resolução do Google Earth pelo
MDT oficial métrico de Santa Catarina!
"""

import os
import zipfile
import io
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from pyproj import Transformer

SOLAR_DIR = r"C:\Users\haas\github\solar"
TIF_PATH = os.path.join(SOLAR_DIR, "MDT_Novo_sitio_das_andorinhas.tif")
KMZ_OUT = os.path.join(SOLAR_DIR, "MDT_3D_Sitio_das_Andorinhas.kmz")

to_wgs = Transformer.from_crs("EPSG:31982", "EPSG:4326", always_xy=True)

def build_collada_dae(x_coords, y_coords, z_grid, step=2):
    """
    Constrói a malha COLLADA 1.4.1 triangulada.
    """
    rows, cols = z_grid.shape
    
    # Centro do modelo
    cx = (x_coords[0] + x_coords[-1]) / 2.0
    cy = (y_coords[0] + y_coords[-1]) / 2.0
    valid_z = z_grid[z_grid != -9999.0]
    z_min = float(np.nanmin(valid_z))
    z_base = z_min

    # Vértices locais (relativos a cx, cy, z_base)
    # Em COLLADA Z_UP: X para leste, Y para norte, Z para cima
    pos_list = []
    uv_list = []
    
    for r in range(rows):
        y_val = float(y_coords[r] - cy)
        v_coord = 1.0 - (r / (rows - 1)) # V de 0 (sul) a 1 (norte)
        for c in range(cols):
            x_val = float(x_coords[c] - cx)
            u_coord = c / (cols - 1)       # U de 0 (oeste) a 1 (leste)
            
            z_val = float(z_grid[r, c])
            if z_val == -9999.0 or np.isnan(z_val):
                z_val = z_base
            z_rel = z_val - z_base
            
            pos_list.extend([f"{x_val:.2f}", f"{y_val:.2f}", f"{z_rel:.2f}"])
            uv_list.extend([f"{u_coord:.4f}", f"{v_coord:.4f}"])

    pos_str = " ".join(pos_list)
    uv_str = " ".join(uv_list)
    pos_count = len(pos_list)
    uv_count = len(uv_list)

    # Triângulos
    tri_list = []
    for r in range(rows - 1):
        for c in range(cols - 1):
            # Índices dos 4 cantos da célula
            i_top_left = r * cols + c
            i_top_right = r * cols + (c + 1)
            i_bot_left = (r + 1) * cols + c
            i_bot_right = (r + 1) * cols + (c + 1)

            # Triângulo 1: top_left -> bot_left -> top_right
            tri_list.extend([
                f"{i_top_left} {i_top_left}",
                f"{i_bot_left} {i_bot_left}",
                f"{i_top_right} {i_top_right}"
            ])
            # Triângulo 2: top_right -> bot_left -> bot_right
            tri_list.extend([
                f"{i_top_right} {i_top_right}",
                f"{i_bot_left} {i_bot_left}",
                f"{i_bot_right} {i_bot_right}"
            ])

    tri_str = " ".join(tri_list)
    tri_count = (rows - 1) * (cols - 1) * 2

    dae = f"""<?xml version="1.0" encoding="utf-8"?>
<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">
  <asset>
    <up_axis>Z_UP</up_axis>
    <unit name="meter" meter="1"/>
  </asset>
  <library_images>
    <image id="tex-img"><init_from>texture.png</init_from></image>
  </library_images>
  <library_effects>
    <effect id="eff">
      <profile_COMMON>
        <newparam sid="surf"><surface type="2D"><init_from>tex-img</init_from></surface></newparam>
        <newparam sid="samp"><sampler2D><source>surf</source></sampler2D></newparam>
        <technique sid="t">
          <lambert>
            <diffuse><texture texture="samp" texcoord="UV"/></diffuse>
          </lambert>
        </technique>
      </profile_COMMON>
    </effect>
  </library_effects>
  <library_materials>
    <material id="mat"><instance_effect url="#eff"/></material>
  </library_materials>
  <library_geometries>
    <geometry id="geo">
      <mesh>
        <source id="pos">
          <float_array id="pos-a" count="{pos_count}">{pos_str}</float_array>
          <technique_common>
            <accessor source="#pos-a" count="{rows * cols}" stride="3">
              <param name="X" type="float"/>
              <param name="Y" type="float"/>
              <param name="Z" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <source id="uv">
          <float_array id="uv-a" count="{uv_count}">{uv_str}</float_array>
          <technique_common>
            <accessor source="#uv-a" count="{rows * cols}" stride="2">
              <param name="S" type="float"/>
              <param name="T" type="float"/>
            </accessor>
          </technique_common>
        </source>
        <vertices id="v">
          <input semantic="POSITION" source="#pos"/>
        </vertices>
        <triangles material="mat" count="{tri_count}">
          <input semantic="VERTEX" source="#v" offset="0"/>
          <input semantic="TEXCOORD" source="#uv" offset="1" set="0"/>
          <p>{tri_str}</p>
        </triangles>
      </mesh>
    </geometry>
  </library_geometries>
  <library_visual_scenes>
    <visual_scene id="scene">
      <node id="n">
        <instance_geometry url="#geo">
          <bind_material>
            <technique_common>
              <instance_material symbol="mat" target="#mat">
                <bind_vertex_input semantic="UV" input_semantic="TEXCOORD" input_set="0"/>
              </instance_material>
            </technique_common>
          </bind_material>
        </instance_geometry>
      </node>
    </visual_scene>
  </library_visual_scenes>
  <scene><instance_visual_scene url="#scene"/></scene>
</COLLADA>
"""
    center_lon, center_lat = to_wgs.transform(cx, cy)
    return dae, center_lon, center_lat, z_base

def gerar_textura_ortofoto(mdt_bounds, elev, nodata):
    """
    Extrai a Ortofoto Oficial do SIGSC (0,39m) exatamente na janela do MDT
    e aplica um relevo sombreado suave para realçar a profundidade 3D.
    """
    orto_path = r"C:\Users\haas\github\SIGSC\raster\ortofoto_sigsc\Orto-RGB_SG-22-Z-D-I-3-SE-A.tif"
    with rasterio.open(orto_path) as orto:
        window = rasterio.windows.from_bounds(mdt_bounds.left, mdt_bounds.bottom, mdt_bounds.right, mdt_bounds.top, orto.transform)
        rgb = orto.read(window=window)

    # Shaded relief para relevo físico 3D
    elev_clean = np.where(elev == nodata, np.nanmin(elev[elev != nodata]), elev)
    gy, gx = np.gradient(elev_clean, 1.0, 1.0)
    slope = np.pi/2.0 - np.arctan(np.sqrt(gx*gx + gy*gy))
    aspect = np.arctan2(-gx, gy)
    shaded = np.sin(np.radians(45.0))*np.sin(slope) + np.cos(np.radians(45.0))*np.cos(slope)*np.cos(np.radians(315.0) - aspect)
    shaded = (shaded - shaded.min()) / (shaded.max() - shaded.min() + 1e-6)
    
    img_shaded = Image.fromarray((shaded * 255).astype(np.uint8)).resize((rgb.shape[2], rgb.shape[1]), Image.Resampling.BILINEAR)
    shaded_arr = np.array(img_shaded) / 255.0
    shaded_3d = np.stack([shaded_arr, shaded_arr, shaded_arr], axis=-1)

    rgb_arr = np.transpose(rgb, (1, 2, 0)).astype(np.float32)
    # 70% foto real + 30% relevo sombreado
    blended = rgb_arr * (0.70 + 0.30 * shaded_3d)
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    tex_img = Image.fromarray(blended)
    
    buf = io.BytesIO()
    tex_img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()

def main():
    print(f"Lendo MDT recortado de {TIF_PATH}...")
    with rasterio.open(TIF_PATH) as src:
        elev = src.read(1)
        nodata = src.nodata
        transform = src.transform
        bounds = src.bounds

    # Subamostragem a 2m (passo = 2) para fluidez perfeita no Google Earth Pro
    step = 2
    elev_sub = elev[::step, ::step]
    rows, cols = elev_sub.shape
    
    # Coordenadas UTM dos pontos da grade
    x_coords = np.array([bounds.left + (c * step + 0.5) * transform.a for c in range(cols)])
    y_coords = np.array([bounds.top + (r * step + 0.5) * transform.e for r in range(rows)])

    print(f"Gerando malha 3D COLLADA ({cols} x {rows} = {cols*rows:,} vértices)...")
    dae_str, c_lon, c_lat, z_base = build_collada_dae(x_coords, y_coords, elev_sub, step=step)

    print("Gerando textura fotográfica 3D oficial do SIGSC (0,39m) com relevo sombreado...")
    tex_bytes = gerar_textura_ortofoto(bounds, elev, nodata)

    doc_kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>MDT 1,0 m Santa Catarina — Sítio das Andorinhas (Terreno 3D Real)</name>
    <Placemark>
      <name>Modelo Digital de Terreno 3D (Substituição de Relevo GE)</name>
      <description><![CDATA[
        <div style="font-family: Arial, sans-serif; min-width: 320px;">
          <h3 style="color: #0b5394;">Modelo Numérico de Terreno Oficial (SDS/SDC 1m)</h3>
          <p>Superfície tridimensional contínua com cota altimétrica métrica real.</p>
          <ul>
            <li><b>Resolução da Malha:</b> 1,0 m / 2,0 m</li>
            <li><b>Extensão:</b> 980 m × 307 m (18,60 ha)</li>
            <li><b>Cota Mínima:</b> {z_base:.1f} m</li>
            <li><b>Cota Máxima:</b> {np.nanmax(elev[elev != nodata]):.1f} m</li>
            <li><b>Modo de Altitude:</b> Absoluta (nível médio do mar)</li>
          </ul>
        </div>
      ]]></description>
      <Model id="model_mdt">
        <altitudeMode>absolute</altitudeMode>
        <Location>
          <longitude>{c_lon:.8f}</longitude>
          <latitude>{c_lat:.8f}</latitude>
          <altitude>{z_base:.2f}</altitude>
        </Location>
        <Orientation>
          <heading>0.0</heading>
          <tilt>0.0</tilt>
          <roll>0.0</roll>
        </Orientation>
        <Scale>
          <x>1.0</x>
          <y>1.0</y>
          <z>1.0</z>
        </Scale>
        <Link>
          <href>model.dae</href>
        </Link>
        <ResourceMap>
          <Alias>
            <targetHref>texture.png</targetHref>
            <sourceHref>texture.png</sourceHref>
          </Alias>
        </ResourceMap>
      </Model>
    </Placemark>
  </Document>
</kml>
"""

    print(f"Empacotando KMZ em {KMZ_OUT}...")
    with zipfile.ZipFile(KMZ_OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', doc_kml.encode('utf-8'))
        z.writestr('model.dae', dae_str.encode('utf-8'))
        z.writestr('texture.png', tex_bytes)

    print(f"SUCESSO! Gerado: {KMZ_OUT} ({os.path.getsize(KMZ_OUT):,} bytes)")

if __name__ == '__main__':
    main()
