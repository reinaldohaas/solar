#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o Projeto Solar Completo em KMZ (Google Earth) com:
1. Remoção TOTAL de camadas do SIGSC (sem modelo 3D Collada, sem curvas de nível SIGSC, sem ortofoto SIGSC)
2. Linha de Divisão e Perímetro do Sítio (18,60 ha) SEGUINDO O TERRENO (clampToGround + tessellate=1)
3. Linhas de Divisão dos Setores P1, P2 e P3 SEGUINDO O TERRENO (clampToGround + tessellate=1)
4. Estruturas 3D (Mesas solares, Salão e Campo de Areia) assentadas diretamente sobre o relevo (relativeToGround)
"""

import os
import zipfile
import geopandas as gpd
from shapely.geometry import Polygon
import numpy as np
from pyproj import Transformer
import xml.etree.ElementTree as ET

SOLAR_DIR = r"C:\Users\haas\github\solar"
GPKG_PATH = os.path.join(SOLAR_DIR, "Projeto_Solar_SIGSC_Nativo.gpkg")
MASTER_KMZ = os.path.join(SOLAR_DIR, "Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz")

to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:31982', always_xy=True)
to_wgs = Transformer.from_crs('EPSG:31982', 'EPSG:4326', always_xy=True)

def densificar_fronteira_clamp(poly_utm, step=8.0):
    """
    Densifica o perímetro a cada 'step' metros para drapeamento suave no terreno do Google Earth.
    Retorna string de coordenadas lon,lat,0
    """
    ext = poly_utm.exterior
    total_len = ext.length
    num_pts = max(int(total_len / step), len(ext.coords))
    
    pts = []
    for d in np.linspace(0, total_len, num_pts):
        pt = ext.interpolate(d)
        lon, lat = to_wgs.transform(pt.x, pt.y)
        pts.append(f"{lon:.7f},{lat:.7f},0")
    return " ".join(pts)

def gerar_divisao_sitio_kml():
    gdf_sitio = gpd.read_file(GPKG_PATH, layer='limite_sitio')
    poly_sitio_utm = gdf_sitio.geometry.iloc[0]
    coords_sitio_str = densificar_fronteira_clamp(poly_sitio_utm, step=8.0)
    
    kml = []
    kml.append('  <Folder>')
    kml.append('    <name>Divisão e Limites do Sítio das Andorinhas</name>')
    kml.append('    <open>1</open>')
    
    # 1. Linha de Divisão Perimetral
    kml.append('    <Placemark>')
    kml.append('      <name>Linha de Divisão do Sítio (18,60 ha - Seguindo o Terreno)</name>')
    kml.append('      <styleUrl>#limite_sitio</styleUrl>')
    kml.append('      <LineString>')
    kml.append('        <tessellate>1</tessellate>')
    kml.append('        <altitudeMode>clampToGround</altitudeMode>')
    kml.append(f'        <coordinates>{coords_sitio_str}</coordinates>')
    kml.append('      </LineString>')
    kml.append('    </Placemark>')

    # 2. Polígono Translúcido Delimitador
    kml.append('    <Placemark>')
    kml.append('      <name>Área Delimitada da Propriedade (18,60 ha)</name>')
    kml.append('      <styleUrl>#poligono_sitio</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <tessellate>1</tessellate>')
    kml.append('        <altitudeMode>clampToGround</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing>')
    kml.append(f'          <coordinates>{coords_sitio_str}</coordinates>')
    kml.append('        </LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # 3. Divisões dos Setores Fotovoltaicos (P1, P2, P3)
    for setor, cor_style in [('P1', '#limite_setor_p1'), ('P2', '#limite_setor_p2'), ('P3', '#limite_setor_p3')]:
        gdf_setor = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor.lower()}')
        poly_setor_utm = gdf_setor.unary_union.convex_hull.buffer(4.0)
        coords_setor_str = densificar_fronteira_clamp(poly_setor_utm, step=6.0)
        
        kml.append('    <Placemark>')
        kml.append(f'      <name>Divisão do Setor {setor} (Área Útil - Seguindo o Terreno)</name>')
        kml.append(f'      <styleUrl>{cor_style}</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <tessellate>1</tessellate>')
        kml.append('        <altitudeMode>clampToGround</altitudeMode>')
        kml.append(f'        <coordinates>{coords_setor_str}</coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')

    kml.append('  </Folder>')
    return '\n'.join(kml)

def gerar_kml_setor_relative(setor):
    gdf = gpd.read_file(GPKG_PATH, layer=f'mesas_ufv_{setor.lower()}')
    num_tables = len(gdf)
    num_modules = num_tables * 14
    dc_power_kwp = num_modules * 0.580
    gen_mwh_ano = dc_power_kwp * 1.36

    # Centroide do setor
    c_utm = gdf.unary_union.centroid
    c_wgs = to_wgs.transform(c_utm.x, c_utm.y)

    table_w = 8.00
    table_d = 4.05

    kml = []
    kml.append('  <Folder>')
    kml.append(f'    <name>UFV {setor.upper()} - {dc_power_kwp:.2f} kWp ({num_tables} mesas / {num_modules} módulos)</name>')
    kml.append('    <open>0</open>')

    # Ficha Técnica / Pin
    kml.append(f'''    <Placemark>
      <name>Ficha Técnica: UFV {setor.upper()}</name>
      <styleUrl>#estilo_pin_solo</styleUrl>
      <description><![CDATA[
        <div style="font-family: Arial, sans-serif; min-width: 300px; line-height: 1.5;">
          <h3 style="color: #0284c7; margin-bottom: 6px;">UFV Solo — Setor {setor.upper()}</h3>
          <p><b>Mesas Fotovoltaicas:</b> {num_tables} mesas (2P × 7 módulos)</p>
          <p><b>Módulos Solares:</b> {num_modules} módulos bifaciais de 580W</p>
          <p><b>Potência Instalada (DC):</b> {dc_power_kwp:.2f} kWp</p>
          <p><b>Inclinação / Orientação:</b> 20° Norte Verdadeiro</p>
          <p><b>Geração Anual Estimada:</b> ~{gen_mwh_ano:,.1f} MWh/ano</p>
        </div>
      ]]></description>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{c_wgs[0]:.7f},{c_wgs[1]:.7f},10.0</coordinates>
      </Point>
    </Placemark>''')

    # Mesas em relativeToGround
    for idx, r in gdf.iterrows():
        mesa_poly = r.geometry
        # Obter cantos da mesa em UTM
        coords = list(mesa_poly.exterior.coords)
        if len(coords) < 4:
            continue
        
        # Encontrar min/max para garantir orientação norte
        xs = [pt[0] for pt in coords[:4]]
        ys = [pt[1] for pt in coords[:4]]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        c_sw = to_wgs.transform(min_x, min_y)
        c_se = to_wgs.transform(max_x, min_y)
        c_ne = to_wgs.transform(max_x, max_y)
        c_nw = to_wgs.transform(min_x, max_y)

        # Alturas relativas ao terreno:
        # Bordo inferior (norte, voltado para o sol na frente): 0.60 m
        # Bordo superior (sul, voltado contra o sol para elevar a parte de trás): 2.15 m (inclinação 20° Norte)
        z_sw, z_se = 2.15, 2.15
        z_nw, z_ne = 0.60, 0.60

        # Superfície do painel solar
        kml.append('    <Placemark>')
        kml.append(f'      <name>{setor.upper()}-Mesa {r["mesa_id"]}</name>')
        kml.append('      <styleUrl>#painel_solo</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {c_sw[0]:.7f},{c_sw[1]:.7f},{z_sw:.2f} {c_se[0]:.7f},{c_se[1]:.7f},{z_se:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},{z_ne:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},{z_nw:.2f} {c_sw[0]:.7f},{c_sw[1]:.7f},{z_sw:.2f}')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')

        # Postes estruturais cravados no solo (relativeToGround 0.0 até o painel)
        kml.append('    <Placemark>')
        kml.append('      <styleUrl>#perna_solo</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {c_sw[0]:.7f},{c_sw[1]:.7f},0.00 {c_sw[0]:.7f},{c_sw[1]:.7f},{z_sw:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},{z_nw:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},0.00')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')
        kml.append('    <Placemark>')
        kml.append('      <styleUrl>#perna_solo</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {c_se[0]:.7f},{c_se[1]:.7f},0.00 {c_se[0]:.7f},{c_se[1]:.7f},{z_se:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},{z_ne:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},0.00')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')

    kml.append('  </Folder>')
    return '\n'.join(kml), num_tables, num_modules, dc_power_kwp, gen_mwh_ano

def gerar_kml_salao_relative():
    # Salão 12,0m x 8,0m (96 m²) ALINHADO rigorosamente com o Campo de Areia (Azimute 118°)
    # Deslocado +2,0 metros para o Norte
    # Centróide UTM: 663449.59, 6968652.91
    c1 = (-49.3469548, -27.3956895) # NW
    c2 = (-49.3468469, -27.3957391) # NE
    c3 = (-49.3468099, -27.3956749) # SE
    c4 = (-49.3469178, -27.3956253) # SW

    u1 = np.array(to_utm.transform(*c1))
    u2 = np.array(to_utm.transform(*c2))
    u3 = np.array(to_utm.transform(*c3))
    u4 = np.array(to_utm.transform(*c4))

    h_wall = 3.60
    h_plat = 4.00

    v_long = (u2 - u1) / np.linalg.norm(u2 - u1)
    v_short = (u4 - u1) / np.linalg.norm(u4 - u1)

    kml = []
    kml.append('  <Folder>')
    kml.append('    <name>Salão 12×8m Aberto (Sem Paredes, Alinhado à Quadra +2m Norte) e Usina Solar (10,44 kWp)</name>')
    kml.append('    <open>0</open>')

    # Ficha Técnica / Pin
    kml.append(f'''    <Placemark>
      <name>Ficha Técnica: Salão 12×8m Aberto e Complexo</name>
      <styleUrl>#estilo_pin_solo</styleUrl>
      <description><![CDATA[
        <div style="font-family: Arial, sans-serif; min-width: 320px; line-height: 1.5;">
          <h3 style="color: #0284c7; margin-bottom: 6px;">Salão de Lazer Aberto (12m × 8m)</h3>
          <p><b>Estrutura:</b> 100% Aberta, sem paredes, sem banheiros nem churrasqueiras no corpo principal</p>
          <p><b>Área Coberta Livre:</b> 96,0 m² (Pé-direito livre de 3,60 m)</p>
          <p><b>Alinhamento:</b> 100% Paralelo ao Campo de Areia (Azimute 118°)</p>
          <p><b>Posicionamento:</b> Deslocado +2,0 m para o Norte</p>
          <p><b>Usina Solar de Cobertura:</b> 18 módulos bifaciais de 580W (10,44 kWp)</p>
        </div>
      ]]></description>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>-49.3468820,-27.3956822,12.0</coordinates>
      </Point>
    </Placemark>''')

    # Pilares estruturais (6 pilares abertos sustentando a cobertura, sem paredes!)
    pillars = [
        u1, (u1 + u2)/2, u2,
        u4, (u4 + u3)/2, u3
    ]
    kml.append('    <Folder><name>Pilares Estruturais (Salão 100% Aberto)</name>')
    for idx, pu in enumerate(pillars):
        pw = to_wgs.transform(*pu)
        kml.append('    <Placemark>')
        kml.append(f'      <name>Pilar {idx+1}</name>')
        kml.append('      <styleUrl>#perna_solo</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {pw[0]:.7f},{pw[1]:.7f},0.00 {pw[0]:.7f},{pw[1]:.7f},{h_wall:.2f}')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')
    kml.append('    </Folder>')

    # Piso / Laje inferior de concreto
    kml.append('    <Placemark>')
    kml.append('      <name>Piso do Salão (12×8m - 96 m² Livres)</name>')
    kml.append('      <styleUrl>#laje</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},0.15 {c2[0]:.7f},{c2[1]:.7f},0.15 {c3[0]:.7f},{c3[1]:.7f},0.15 {c4[0]:.7f},{c4[1]:.7f},0.15 {c1[0]:.7f},{c1[1]:.7f},0.15')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Cobertura plana
    kml.append('    <Placemark>')
    kml.append('      <name>Cobertura do Salão Aberto (96 m²)</name>')
    kml.append('      <styleUrl>#platibanda</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{h_wall:.2f} {c2[0]:.7f},{c2[1]:.7f},{h_wall:.2f} {c3[0]:.7f},{c3[1]:.7f},{h_wall:.2f} {c4[0]:.7f},{c4[1]:.7f},{h_wall:.2f} {c1[0]:.7f},{c1[1]:.7f},{h_wall:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Módulos Solares (18 módulos = 2 fileiras x 9 módulos)
    kml.append('    <Folder><name>Usina Solar de Cobertura (18 Módulos - 10,44 kWp)</name>')
    mod_w = 1.134
    mod_d = 2.278
    tilt_rad = np.radians(18.0)
    d_proj_y = mod_d * np.cos(tilt_rad)
    z_rise = mod_d * np.sin(tilt_rad)

    margin_x = 0.70
    gap_mod = 0.05
    row_pitch_y = 3.20
    z_base_mount = h_wall + 0.15

    for row in range(2):
        y_start_u = u1 + (row * row_pitch_y + 1.20) * v_short
        for col in range(9):
            x_start_u = y_start_u + (margin_x + col * (mod_w + gap_mod)) * v_long
            p_sw_u = x_start_u
            p_se_u = x_start_u + mod_w * v_long
            p_nw_u = np.array([p_sw_u[0], p_sw_u[1] + d_proj_y])
            p_ne_u = np.array([p_se_u[0], p_se_u[1] + d_proj_y])

            p_sw = to_wgs.transform(*p_sw_u)
            p_se = to_wgs.transform(*p_se_u)
            p_ne = to_wgs.transform(*p_ne_u)
            p_nw = to_wgs.transform(*p_nw_u)

            kml.append('    <Placemark>')
            kml.append(f'      <name>Módulo R{row+1}-C{col+1}</name>')
            kml.append('      <styleUrl>#painel_solar</styleUrl>')
            kml.append('      <Polygon>')
            kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
            kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
            kml.append(f'          {p_sw[0]:.7f},{p_sw[1]:.7f},{z_base_mount+z_rise:.2f} {p_se[0]:.7f},{p_se[1]:.7f},{z_base_mount+z_rise:.2f} {p_ne[0]:.7f},{p_ne[1]:.7f},{z_base_mount:.2f} {p_nw[0]:.7f},{p_nw[1]:.7f},{z_base_mount:.2f} {p_sw[0]:.7f},{p_sw[1]:.7f},{z_base_mount+z_rise:.2f}')
            kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
            kml.append('      </Polygon>')
            kml.append('    </Placemark>')
    kml.append('    </Folder>')
    kml.append('  </Folder>')
    return '\n'.join(kml)

def gerar_kml_campo_relative():
    # Campo 22x12m deslocado +2,0 metros para o Norte
    # Centróide UTM: 663468.93, 6968640.32
    cx, cy = 663468.93, 6968640.32
    center = np.array([cx, cy])

    az_rad = np.radians(118.0)
    v_l = np.array([np.sin(az_rad), np.cos(az_rad)])
    v_w = np.array([-np.cos(az_rad), np.sin(az_rad)])

    L = 22.0
    W = 12.0
    H_net = 6.00

    c1_u = center - (L/2)*v_l - (W/2)*v_w
    c2_u = center + (L/2)*v_l - (W/2)*v_w
    c3_u = center + (L/2)*v_l + (W/2)*v_w
    c4_u = center - (L/2)*v_l + (W/2)*v_w

    c1 = to_wgs.transform(*c1_u)
    c2 = to_wgs.transform(*c2_u)
    c3 = to_wgs.transform(*c3_u)
    c4 = to_wgs.transform(*c4_u)

    kml = []
    kml.append('  <Folder>')
    kml.append('    <name>Campo de Futebol e Vôlei de Areia (Redes 3D)</name>')
    kml.append('    <open>0</open>')

    # Caixa de areia
    kml.append('    <Placemark>')
    kml.append('      <name>Caixa de Areia (22,0 m × 12,0 m)</name>')
    kml.append('      <styleUrl>#areia</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <tessellate>1</tessellate>')
    kml.append('        <altitudeMode>clampToGround</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},0.0 {c2[0]:.7f},{c2[1]:.7f},0.0 {c3[0]:.7f},{c3[1]:.7f},0.0 {c4[0]:.7f},{c4[1]:.7f},0.0 {c1[0]:.7f},{c1[1]:.7f},0.0')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Redes perimetrais 6m
    sides = [
        (c1, c2, 'Rede Lateral Sul (22m)'),
        (c2, c3, 'Rede Fundo Leste (12m)'),
        (c3, c4, 'Rede Lateral Norte (22m)'),
        (c4, c1, 'Rede Fundo Oeste (12m)')
    ]
    kml.append('    <Folder><name>Redes de Proteção Perimetrais (ao redor - 6m)</name>')
    for p_a, p_b, sname in sides:
        kml.append('    <Placemark>')
        kml.append(f'      <name>{sname}</name>')
        kml.append('      <styleUrl>#rede_perimetral</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {p_a[0]:.7f},{p_a[1]:.7f},0.00 {p_b[0]:.7f},{p_b[1]:.7f},0.00 {p_b[0]:.7f},{p_b[1]:.7f},{H_net:.2f} {p_a[0]:.7f},{p_a[1]:.7f},{H_net:.2f} {p_a[0]:.7f},{p_a[1]:.7f},0.00')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')
    kml.append('    </Folder>')

    # Rede de teto
    kml.append('    <Placemark>')
    kml.append('      <name>Rede de Proteção Superior (teto anti-fuga - 6m)</name>')
    kml.append('      <styleUrl>#rede_teto</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>relativeToGround</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{H_net:.2f} {c2[0]:.7f},{c2[1]:.7f},{H_net:.2f} {c3[0]:.7f},{c3[1]:.7f},{H_net:.2f} {c4[0]:.7f},{c4[1]:.7f},{H_net:.2f} {c1[0]:.7f},{c1[1]:.7f},{H_net:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')
    kml.append('  </Folder>')
    return '\n'.join(kml)

def get_cardinal(deg):
    dirs = ['N', 'NNE', 'NE', 'ENE', 'L', 'ESE', 'SE', 'SSE', 'S', 'SSO', 'SO', 'OSO', 'O', 'ONO', 'NO', 'NNO', 'N']
    idx = int(round(deg / 22.5)) % 16
    return dirs[idx]

def gerar_kml_simulacao_solar_3d():
    lat_c, lon_c = -27.3957000, -49.3468500
    R = 850.0
    elev_ground = 530.0

    def sol_vector(d, h):
        lat_rad = np.radians(lat_c)
        b = np.radians((360.0 / 365.0) * (d - 81))
        decl = np.radians(23.45 * np.sin(b))
        eot = 9.87 * np.sin(2 * b) - 7.53 * np.cos(b) - 1.5 * np.sin(b)
        solar_time = h + (4.0 * (lon_c - (-45.0)) + eot) / 60.0
        omega = np.radians((solar_time - 12.0) * 15.0)
        v_east = -np.cos(decl) * np.sin(omega)
        v_north = -np.sin(lat_rad) * np.cos(decl) * np.cos(omega) + np.cos(lat_rad) * np.sin(decl)
        v_up = np.cos(lat_rad) * np.cos(decl) * np.cos(omega) + np.sin(lat_rad) * np.sin(decl)
        altitude = np.degrees(np.arcsin(np.clip(v_up, -1.0, 1.0)))
        azimuth = np.degrees(np.arctan2(v_east, v_north)) % 360.0
        return altitude, azimuth, v_east, v_north, v_up

    kml = []
    kml.append('  <Folder>')
    kml.append('    <name>Simulação e Carta Solar 3D (Caminho do Sol no Sítio)</name>')
    kml.append('    <open>0</open>')
    kml.append('''    <description><![CDATA[
      <div style="font-family: Arial, sans-serif; min-width: 320px; line-height: 1.5;">
        <h3 style="color: #d97706; margin-bottom: 6px;">Carta Solar Tridimensional e Sombras</h3>
        <p><b>Localização:</b> Sítio das Andorinhas (Lat: -27.3957° S, Lon: -49.3468° O)</p>
        <p><b>Trajetórias Celestes:</b> Modeladas na abóbada celeste acima do complexo fotovoltaico.</p>
        <hr style="border: 0; border-top: 1px solid #ccc; margin: 8px 0;"/>
        <ul>
          <li><b style="color: #eab308;">Solstício de Verão (21/Dez):</b> Arco solar mais alto, atingindo altitude máxima de ~85° (quase zênite).</li>
          <li><b style="color: #f97316;">Equinócios (21/Mar e 22/Set):</b> Arco intermediário, atingindo altitude máxima de ~62,6° ao meio-dia.</li>
          <li><b style="color: #0284c7;">Solstício de Inverno (21/Jun):</b> Arco mais baixo ao Norte (~39,2° ao meio-dia), definindo o pior caso de espaçamento entre fileiras.</li>
        </ul>
        <hr style="border: 0; border-top: 1px solid #ccc; margin: 8px 0;"/>
        <p><i><b>DICA DE ENGENHARIA:</b> Ative o recurso nativo de "Sol" no Google Earth Pro (menu <b>Visualizar -> Sol</b>) para verificar a projeção das sombras reais do terreno e das mesas solares em qualquer data e horário!</i></p>
      </div>
    ]]></description>''')

    # Marcador de ativação do Sol Nativo
    kml.append(f'''    <Placemark>
      <name>☀️ GUIA: Ativar Sol e Sombras no Google Earth Pro</name>
      <styleUrl>#pin_sol_guia</styleUrl>
      <description><![CDATA[
        <div style="font-family: Arial, sans-serif; min-width: 300px; line-height: 1.5;">
          <h4 style="color: #0284c7; margin-bottom: 6px;">Como Ativar Sombras Dinâmicas no Google Earth Pro:</h4>
          <ol style="margin-left: 18px; margin-bottom: 8px;">
            <li>No menu superior do Google Earth Pro, clique em <b>Visualizar</b> e marque <b>Sol</b> (ou atalho <code>Ctrl + Alt + S</code>).</li>
            <li>Uma barra de controle de tempo aparecerá no canto superior esquerdo.</li>
            <li>Arraste o cursor deslizante para alterar o horário do dia e a data do ano.</li>
            <li>Observe a projeção em tempo real das sombras das mesas solares e do relevo montanhoso!</li>
          </ol>
        </div>
      ]]></description>
      <Point>
        <altitudeMode>relativeToGround</altitudeMode>
        <coordinates>{lon_c:.7f},{lat_c:.7f},25.0</coordinates>
      </Point>
    </Placemark>''')

    seasons = [
        ('Solstício de Verão (21 de Dezembro - Sol Alto ~85°)', 355, 'sol_verao', 'marcador_sol_verao'),
        ('Equinócios de Outono e Primavera (21/Mar e 22/Set - ~63°)', 80, 'sol_equinocio', 'marcador_sol_equinocio'),
        ('Solstício de Inverno (21 de Junho - Sol Baixo ~39°)', 172, 'sol_inverno', 'marcador_sol_inverno')
    ]

    for s_name, d_val, style_line, style_pin in seasons:
        kml.append('    <Folder>')
        kml.append(f'      <name>{s_name}</name>')
        kml.append('      <open>0</open>')

        # Traçar linha contínua do arco celeste
        arc_pts = []
        for h in np.linspace(5.5, 18.5, 80):
            alt, az, ve, vn, vu = sol_vector(d_val, h)
            if vu > -0.05:
                d_east = R * ve
                d_north = R * vn
                d_up = elev_ground + R * max(0.0, vu)
                lon_pt = lon_c + d_east / (111139.0 * np.cos(np.radians(lat_c)))
                lat_pt = lat_c + d_north / 111139.0
                arc_pts.append(f'{lon_pt:.7f},{lat_pt:.7f},{d_up:.1f}')

        if arc_pts:
            kml.append('      <Placemark>')
            kml.append(f'        <name>Trajetória 3D do Sol - {s_name.split("(")[0].strip()}</name>')
            kml.append(f'        <styleUrl>#{style_line}</styleUrl>')
            kml.append('        <LineString>')
            kml.append('          <altitudeMode>absolute</altitudeMode>')
            kml.append(f'          <coordinates>{" ".join(arc_pts)}</coordinates>')
            kml.append('        </LineString>')
            kml.append('      </Placemark>')

        # Marcadores horários ao longo do arco
        for h in [6.0, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0]:
            alt, az, ve, vn, vu = sol_vector(d_val, h)
            if vu > 0.05:
                d_east = R * ve
                d_north = R * vn
                d_up = elev_ground + R * vu
                lon_pt = lon_c + d_east / (111139.0 * np.cos(np.radians(lat_c)))
                lat_pt = lat_c + d_north / 111139.0
                
                # Fator de incidência solar em mesas inclinadas a 20° Norte
                cos_incid = np.clip(vn * np.sin(np.radians(20.0)) + vu * np.cos(np.radians(20.0)), 0.0, 1.0)
                eficiencia_angular = cos_incid * 100.0
                shadow_ratio = 1.0 / np.tan(np.radians(max(3.0, alt)))

                h_int = int(h)
                m_int = int((h - h_int) * 60)
                h_str = f'{h_int:02d}:{m_int:02d}'

                kml.append(f'''      <Placemark>
        <name>Sol às {h_str} ({alt:.1f}° / Az: {az:.1f}°)</name>
        <styleUrl>#{style_pin}</styleUrl>
        <description><![CDATA[
          <div style="font-family: Arial, sans-serif; min-width: 270px; line-height: 1.5;">
            <h4 style="color: #d97706; margin-bottom: 4px;">Posição Solar: {h_str}</h4>
            <p><b>Data / Estação:</b> {s_name.split("(")[0].strip()}</p>
            <p><b>Altitude Solar (Elevação):</b> {alt:.1f}° acima do horizonte</p>
            <p><b>Azimute Solar:</b> {az:.1f}° ({get_cardinal(az)})</p>
            <p><b>Incidência nas Mesas 20° Norte:</b> {eficiencia_angular:.1f}%</p>
            <p><b>Multiplicador de Sombra:</b> {shadow_ratio:.2f} × altura</p>
          </div>
        ]]></description>
        <Point>
          <altitudeMode>absolute</altitudeMode>
          <coordinates>{lon_pt:.7f},{lat_pt:.7f},{d_up:.1f}</coordinates>
        </Point>
      </Placemark>''')

        kml.append('    </Folder>')

    kml.append('  </Folder>')
    return '\n'.join(kml)

def gerar_kml_ortofoto_drone():
    """Gera apenas a Ortofoto do Drone de Alta Resolução sem nenhuma linha ou estação de voo."""
    kml = []
    kml.append('  <Folder>')
    kml.append('    <name>Ortofoto do Drone de Alta Resolução</name>')
    kml.append('    <visibility>1</visibility>')
    kml.append('    <open>0</open>')
    kml.append('    <NetworkLink>')
    kml.append('      <name>Ortofoto do Drone (01/06/2024 - Estrada e Sítio)</name>')
    kml.append('      <visibility>1</visibility>')
    kml.append('      <open>0</open>')
    kml.append('      <Link>')
    kml.append('        <href>Estrada-Ribeiro-dos-Ovos-01-06-2024-orthophoto_1.kmz</href>')
    kml.append('        <viewRefreshMode>onRegion</viewRefreshMode>')
    kml.append('      </Link>')
    kml.append('    </NetworkLink>')
    kml.append('  </Folder>')
    return '\n'.join(kml)

def exportar_kmz_fotos_drone_separado():
    """Exporta as fotos pontuais do drone em um arquivo KMZ AVULSO (Fotos_Drone_DCIM_Opcional.kmz),
    mantendo o Projeto Solar Completo 100% limpo de trajetórias e estações de voo."""
    import json
    cache_path = os.path.join(SOLAR_DIR, 'fotos_drone_dcim_cache.json')
    if not os.path.exists(cache_path):
        return
    
    with open(cache_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    folder_titles = {
        '100MEDIA': ('Voo 2024 - Estrada e Sítio (01/06/2024)', 'camera_100'),
        '109MEDIA': ('Voo 2026 - Acesso e Usinas (01/03/2026)', 'camera_109'),
        '110MEDIA': ('Voo 2026 - Salão e Campo de Areia (01/03/2026)', 'camera_110'),
        '111MEDIA': ('Voo 2026 - Setor Leste e Pastagem (01/03/2026)', 'camera_111')
    }

    kml = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2">', '<Document>']
    kml.append('  <name>Fotos do Drone - Acervo DCIM (Opcional Avulso)</name>')
    kml.append('  <open>0</open>')
    kml.append('''
  <Style id="camera_100"><IconStyle><scale>0.65</scale><color>ff00bbff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/camera.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
  <Style id="camera_109"><IconStyle><scale>0.65</scale><color>ffffbb00</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/camera.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
  <Style id="camera_110"><IconStyle><scale>0.75</scale><color>ffff00ff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/camera.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
  <Style id="camera_111"><IconStyle><scale>0.65</scale><color>ff00ff88</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/camera.png</href></Icon></IconStyle><LabelStyle><scale>0</scale></LabelStyle></Style>
''')
    for f_key, (f_title, style_id) in folder_titles.items():
        photos = data.get(f_key, [])
        if not photos:
            continue
        kml.append('    <Folder>')
        kml.append(f'      <name>{f_key}: {f_title} ({len(photos)} fotos)</name>')
        kml.append('      <visibility>0</visibility>')
        kml.append('      <open>0</open>')
        for p in photos:
            fname = p['file']
            ppath = p['path']
            lat, lon, alt = p['lat'], p['lon'], p['alt']
            dt = p['dt']
            kml.append(f'''      <Placemark>
        <name>{fname}</name>
        <styleUrl>#{style_id}</styleUrl>
        <description><![CDATA[
          <div style="font-family: Arial, sans-serif; min-width: 280px; line-height: 1.5;">
            <h4 style="color: #0284c7; margin-bottom: 4px;">Foto: {fname}</h4>
            <p style="margin: 3px 0;"><b>Pasta:</b> D:\\drone\\DCIM\\{f_key}</p>
            <p style="margin: 3px 0;"><b>Data/Hora:</b> {dt}</p>
            <p style="margin: 3px 0;"><b>Altitude do Voo (MSL):</b> {alt} m</p>
            <p style="margin: 3px 0;"><b>Coordenadas:</b> {lat:.6f}, {lon:.6f}</p>
            <hr style="border: 0; border-top: 1px solid #ddd; margin: 8px 0;"/>
            <p style="margin: 6px 0;"><a href="file:///{ppath}" target="_blank" style="color: #0284c7; font-weight: bold; text-decoration: underline;">📷 Abrir Foto Original em Alta Resolução (D:\\)</a></p>
          </div>
        ]]></description>
        <Point>
          <altitudeMode>clampToGround</altitudeMode>
          <coordinates>{lon:.7f},{lat:.7f},0</coordinates>
        </Point>
      </Placemark>''')
        kml.append('    </Folder>')
    kml.append('</Document>')
    kml.append('</kml>')

    out_kmz = os.path.join(SOLAR_DIR, 'Fotos_Drone_DCIM_Opcional.kmz')
    with zipfile.ZipFile(out_kmz, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', '\n'.join(kml).encode('utf-8'))
    print(f"KMZ Avulso de Fotos do Drone gerado: {out_kmz}")

def main():
    print("1. Gerando Setores Solares em relativeToGround...")
    kml_p1, t1, m1, kw1, gen1 = gerar_kml_setor_relative("P1")
    kml_p2, t2, m2, kw2, gen2 = gerar_kml_setor_relative("P2")
    kml_p3, t3, m3, kw3, gen3 = gerar_kml_setor_relative("P3")

    tot_tables = t1 + t2 + t3
    tot_modules = m1 + m2 + m3
    tot_dc_kwp = kw1 + kw2 + kw3
    tot_gen_mwh = gen1 + gen2 + gen3

    print("2. Gerando Linha de Divisão do Sítio seguindo o Terreno...")
    kml_divisao = gerar_divisao_sitio_kml()

    print("3. Gerando Salão e Campo de Areia...")
    kml_salao = gerar_kml_salao_relative()
    kml_campo = gerar_kml_campo_relative()

    print("4. Gerando Ortofoto de Drone de Alta Resolução...")
    kml_drone = gerar_kml_ortofoto_drone()
    exportar_kmz_fotos_drone_separado()

    print("5. Gerando Simulação e Carta Solar 3D...")
    kml_sol = gerar_kml_simulacao_solar_3d()

    print("6. Montando Master KMZ...")
    master_kml = []
    master_kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    master_kml.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">')
    master_kml.append('<Document>')
    master_kml.append('  <name>Projeto Solar Completo - Sítio das Andorinhas</name>')
    master_kml.append('  <open>1</open>')

    master_kml.append('''
  <Style id="limite_sitio">
    <LineStyle><color>ffffea00</color><width>4.0</width></LineStyle>
  </Style>
  <Style id="poligono_sitio">
    <LineStyle><color>ffffea00</color><width>1.8</width></LineStyle>
    <PolyStyle><color>22ffff00</color><fill>1</fill><outline>1</outline></PolyStyle>
  </Style>
  <Style id="limite_setor_p1">
    <LineStyle><color>ff0284c7</color><width>3.0</width></LineStyle>
  </Style>
  <Style id="limite_setor_p2">
    <LineStyle><color>ff059669</color><width>3.0</width></LineStyle>
  </Style>
  <Style id="limite_setor_p3">
    <LineStyle><color>ffd97706</color><width>3.0</width></LineStyle>
  </Style>
  <Style id="painel_solo">
    <LineStyle><color>ffd0d0d0</color><width>1.0</width></LineStyle>
    <PolyStyle><color>ffd55018</color></PolyStyle>
  </Style>
  <Style id="perna_solo">
    <LineStyle><color>ff777777</color><width>1.6</width></LineStyle>
  </Style>
  <Style id="parede">
    <LineStyle><color>ff333333</color><width>1.5</width></LineStyle>
    <PolyStyle><color>ffebebeb</color></PolyStyle>
  </Style>
  <Style id="platibanda">
    <LineStyle><color>ff222222</color><width>1.8</width></LineStyle>
    <PolyStyle><color>ff555555</color></PolyStyle>
  </Style>
  <Style id="laje">
    <LineStyle><color>ff444444</color><width>1.2</width></LineStyle>
    <PolyStyle><color>ff999999</color></PolyStyle>
  </Style>
  <Style id="painel_solar">
    <LineStyle><color>ffd0d0d0</color><width>1.0</width></LineStyle>
    <PolyStyle><color>ffd55018</color></PolyStyle>
  </Style>
  <Style id="areia">
    <LineStyle><color>ffd0a030</color><width>1.5</width></LineStyle>
    <PolyStyle><color>bf45b5d8</color></PolyStyle>
  </Style>
  <Style id="rede_perimetral">
    <LineStyle><color>aa444444</color><width>1.2</width></LineStyle>
    <PolyStyle><color>44333333</color></PolyStyle>
  </Style>
  <Style id="rede_teto">
    <LineStyle><color>88444444</color><width>1.0</width></LineStyle>
    <PolyStyle><color>33222222</color></PolyStyle>
  </Style>
  <Style id="estilo_pin_solo">
    <IconStyle>
      <scale>1.3</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
      <color>ff11ccff</color>
    </IconStyle>
  </Style>
  <Style id="painel_info">
    <IconStyle>
      <scale>1.5</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
      <color>ff00ffff</color>
    </IconStyle>
  </Style>
  <Style id="sol_verao"><LineStyle><color>ff00d7ff</color><width>3.5</width></LineStyle></Style>
  <Style id="sol_equinocio"><LineStyle><color>ff00a5ff</color><width>3.0</width></LineStyle></Style>
  <Style id="sol_inverno"><LineStyle><color>ffffc000</color><width>3.5</width></LineStyle></Style>
  <Style id="marcador_sol_verao"><IconStyle><scale>1.1</scale><color>ff00d7ff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/sun.png</href></Icon></IconStyle></Style>
  <Style id="marcador_sol_equinocio"><IconStyle><scale>1.0</scale><color>ff00a5ff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/sun.png</href></Icon></IconStyle></Style>
  <Style id="marcador_sol_inverno"><IconStyle><scale>1.1</scale><color>ffffc000</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/sun.png</href></Icon></IconStyle></Style>
  <Style id="pin_sol_guia"><IconStyle><scale>1.4</scale><color>ff00ffff</color><Icon><href>http://maps.google.com/mapfiles/kml/shapes/sun.png</href></Icon></IconStyle></Style>
''')

    # Ficha Geral / Resumo Executivo
    master_kml.append(f'''
  <Placemark>
    <name>★ RESUMO EXECUTIVO: Complexo Solar Sítio das Andorinhas (~1,90 MWp)</name>
    <styleUrl>#painel_info</styleUrl>
    <description><![CDATA[
      <div style="font-family: Arial, sans-serif; min-width: 380px; line-height: 1.5;">
        <h2 style="color: #0b5394; border-bottom: 2px solid #0b5394; padding-bottom: 6px; margin-bottom: 12px;">
          Complexo Fotovoltaico Sítio das Andorinhas
        </h2>
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <tr style="background-color: #f2f2f2;">
            <th style="padding: 6px; border: 1px solid #999;">Setor</th>
            <th style="padding: 6px; border: 1px solid #999;">Mesas</th>
            <th style="padding: 6px; border: 1px solid #999;">Módulos</th>
            <th style="padding: 6px; border: 1px solid #999;">Potência (kWp)</th>
            <th style="padding: 6px; border: 1px solid #999;">Geração Anual</th>
          </tr>
          <tr>
            <td style="padding: 5px; border: 1px solid #ddd;"><b>Solo P1 (Redistribuído)</b></td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{t1}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{m1}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{kw1:.2f} kWp</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">~{gen1:,.1f} MWh</td>
          </tr>
          <tr style="background-color: #f9f9f9;">
            <td style="padding: 5px; border: 1px solid #ddd;"><b>Solo P2</b></td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{t2}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{m2}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{kw2:.2f} kWp</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">~{gen2:,.1f} MWh</td>
          </tr>
          <tr>
            <td style="padding: 5px; border: 1px solid #ddd;"><b>Solo P3</b></td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{t3}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{m3}</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">{kw3:.2f} kWp</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">~{gen3:,.1f} MWh</td>
          </tr>
          <tr style="background-color: #f9f9f9;">
            <td style="padding: 5px; border: 1px solid #ddd;"><b>Salão (Cobertura Plana)</b></td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">2 arranjos</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">18</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">10,44 kWp</td>
            <td style="padding: 5px; border: 1px solid #ddd; text-align: center;">~14,2 MWh</td>
          </tr>
          <tr style="background-color: #e6f2ff; font-weight: bold;">
            <td style="padding: 8px; border: 1px solid #999;">TOTAL GERAL</td>
            <td style="padding: 8px; border: 1px solid #999; text-align: center;">{tot_tables} + cob</td>
            <td style="padding: 8px; border: 1px solid #999; text-align: center;">{tot_modules + 18:,}</td>
            <td style="padding: 8px; border: 1px solid #999; text-align: center;">{(tot_dc_kwp + 10.44):,.2f} kWp (~1,90 MWp)</td>
            <td style="padding: 8px; border: 1px solid #999; text-align: center;">{(tot_gen_mwh + 14.2):,.1f} MWh/ano</td>
          </tr>
        </table>
      </div>
    ]]></description>
    <Point>
      <altitudeMode>relativeToGround</altitudeMode>
      <coordinates>-49.3468500,-27.3957000,15.0</coordinates>
    </Point>
  </Placemark>
''')

    # Adicionar Divisão do Sítio
    master_kml.append(kml_divisao)

    # Adicionar Salão
    master_kml.append(kml_salao)

    # Adicionar Campo de Areia
    master_kml.append(kml_campo)

    # Adicionar Usinas de Solo P1, P2 e P3
    master_kml.append('  <Folder>')
    master_kml.append(f'    <name>Usina Solar Solo - Complexo P1, P2 e P3 ({tot_dc_kwp:.2f} kWp)</name>')
    master_kml.append('    <open>1</open>')
    master_kml.append(kml_p1)
    master_kml.append(kml_p2)
    master_kml.append(kml_p3)
    master_kml.append('  </Folder>')

    # Adicionar Simulação e Carta Solar 3D
    master_kml.append(kml_sol)

    # Adicionar Ortofoto de Drone de Alta Resolução
    if kml_drone:
        master_kml.append(kml_drone)

    master_kml.append('</Document>')
    master_kml.append('</kml>')

    with zipfile.ZipFile(MASTER_KMZ, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', '\n'.join(master_kml).encode('utf-8'))

    print(f"MASTER KMZ GERADO COM SUCESSO: {MASTER_KMZ}")
    sz_kb = os.path.getsize(MASTER_KMZ) / 1024
    print(f"Tamanho do arquivo KMZ: {sz_kb:.1f} KB")

    # Exportar também arquivos KMZ individuais limpos
    styles_common = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <Style id="limite_sitio"><LineStyle><color>ffffea00</color><width>4.0</width></LineStyle></Style>
  <Style id="poligono_sitio"><LineStyle><color>ffffea00</color><width>1.8</width></LineStyle><PolyStyle><color>22ffff00</color><fill>1</fill><outline>1</outline></PolyStyle></Style>
  <Style id="limite_setor_p1"><LineStyle><color>ff0284c7</color><width>3.0</width></LineStyle></Style>
  <Style id="limite_setor_p2"><LineStyle><color>ff059669</color><width>3.0</width></LineStyle></Style>
  <Style id="limite_setor_p3"><LineStyle><color>ffd97706</color><width>3.0</width></LineStyle></Style>
  <Style id="painel_solo"><LineStyle><color>ffd0d0d0</color><width>1.0</width></LineStyle><PolyStyle><color>ffd55018</color></PolyStyle></Style>
  <Style id="perna_solo"><LineStyle><color>ff777777</color><width>1.6</width></LineStyle></Style>
  <Style id="parede"><LineStyle><color>ff333333</color><width>1.5</width></LineStyle><PolyStyle><color>ffebebeb</color></PolyStyle></Style>
  <Style id="platibanda"><LineStyle><color>ff222222</color><width>1.8</width></LineStyle><PolyStyle><color>ff555555</color></PolyStyle></Style>
  <Style id="laje"><LineStyle><color>ff444444</color><width>1.2</width></LineStyle><PolyStyle><color>ff999999</color></PolyStyle></Style>
  <Style id="painel_solar"><LineStyle><color>ffd0d0d0</color><width>1.0</width></LineStyle><PolyStyle><color>ffd55018</color></PolyStyle></Style>
  <Style id="areia"><LineStyle><color>ffd0a030</color><width>1.5</width></LineStyle><PolyStyle><color>bf45b5d8</color></PolyStyle></Style>
  <Style id="rede_perimetral"><LineStyle><color>aa444444</color><width>1.2</width></LineStyle><PolyStyle><color>44333333</color></PolyStyle></Style>
  <Style id="rede_teto"><LineStyle><color>88444444</color><width>1.0</width></LineStyle><PolyStyle><color>33222222</color></PolyStyle></Style>
  <Style id="estilo_pin_solo"><IconStyle><scale>1.3</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon><color>ff11ccff</color></IconStyle></Style>
'''
    for name, content in [
        ('projeto_solar_p1.kmz', kml_p1),
        ('projeto_solar_p2.kmz', kml_p2),
        ('projeto_solar_p3.kmz', kml_p3),
        ('salao_telhado_reto_com_solar.kmz', kml_salao),
        ('Campo_de_areia_modelado_com_redes.kmz', kml_campo),
        ('Divisao_Sitio_das_Andorinhas.kmz', kml_divisao),
        ('Simulacao_Carta_Solar_3D.kmz', kml_sol)
    ]:
        kpath = os.path.join(SOLAR_DIR, name)
        full_doc = styles_common + content + '\n</Document>\n</kml>'
        with zipfile.ZipFile(kpath, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('doc.kml', full_doc.encode('utf-8'))
        print(f"KMZ Individual Atualizado: {kpath}")

if __name__ == '__main__':
    main()
