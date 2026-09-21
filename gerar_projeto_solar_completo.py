#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJETO DE ENERGIA SOLAR E MODELAGEM 3D - SÍTIO DAS ANDORINHAS
===============================================================================
Reprojeta todos os elementos com COTA ALTIMÉTRICA ABSOLUTA (altitudeMode: absolute)
amostrada diretamente do MDT Oficial de 1 metro de Santa Catarina (SDS/SDC - SIGSC),
garantindo compatibilidade 1:1 com o terreno real e a ortofoto de alta definição,
sem depender do relevo de baixa resolução nativo do Google Earth.
"""

import os
import zipfile
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Polygon, box, Point, LineString
import xml.etree.ElementTree as ET
from pyproj import Transformer

SOLAR_DIR = r"C:\Users\haas\github\solar"
MDT_PATH = os.path.join(SOLAR_DIR, "MDT_Novo_sitio_das_andorinhas.tif")

# Transformadores de coordenadas
to_utm = Transformer.from_crs("EPSG:4326", "EPSG:31982", always_xy=True)
to_wgs = Transformer.from_crs("EPSG:31982", "EPSG:4326", always_xy=True)

def parse_kmz_polygon(kmz_path):
    with zipfile.ZipFile(kmz_path, 'r') as z:
        for n in z.namelist():
            if n.endswith('.kml'):
                root = ET.fromstring(z.read(n))
                for c in root.iter('{http://www.opengis.net/kml/2.2}coordinates'):
                    pts = [[float(x) for x in pt.split(',')][:2] for pt in c.text.strip().split()]
                    if len(pts) >= 3:
                        return Polygon(pts)
    raise ValueError(f"Não foi possível extrair polígono de {kmz_path}")

def get_mdt_sampler():
    """
    Retorna uma função de amostragem bilinear contínua sobre o MDT 1,0 m do SIGSC.
    """
    with rasterio.open(MDT_PATH) as src:
        elev = src.read(1)
        bounds = src.bounds
        transform = src.transform
        nodata = src.nodata

    def sample(x, y):
        c_flt = (x - bounds.left) / transform.a - 0.5
        r_flt = (y - bounds.top) / transform.e - 0.5
        c0 = max(0, min(int(np.floor(c_flt)), elev.shape[1] - 1))
        r0 = max(0, min(int(np.floor(r_flt)), elev.shape[0] - 1))
        c1 = min(c0 + 1, elev.shape[1] - 1)
        r1 = min(r0 + 1, elev.shape[0] - 1)
        dc = c_flt - c0
        dr = r_flt - r0
        z00, z01 = elev[r0, c0], elev[r0, c1]
        z10, z11 = elev[r1, c0], elev[r1, c1]
        top = z00 * (1 - dc) + z01 * dc
        bot = z10 * (1 - dc) + z11 * dc
        val = float(top * (1 - dr) + bot * dr)
        return val if (val != nodata and not np.isnan(val)) else 550.0

    return sample

def densificar_fronteira_3d(poly_wgs84, sampler, dz=0.35, step=8.0):
    """
    Densifica o polígono perimetral a cada passo de 'step' metros e projeta
    na cota real do MDT + dz, em modo altitudeMode: absolute.
    """
    gdf = gpd.GeoDataFrame([{'geometry': poly_wgs84}], crs='EPSG:4326').to_crs('EPSG:31982')
    geom_utm = gdf.geometry.iloc[0]
    ext = geom_utm.exterior
    total_len = ext.length
    num_pts = max(int(total_len / step), 12)
    
    pts_3d = []
    for d in np.linspace(0, total_len, num_pts):
        pt = ext.interpolate(d)
        z = sampler(pt.x, pt.y) + dz
        lon, lat = to_wgs.transform(pt.x, pt.y)
        pts_3d.append(f"{lon:.7f},{lat:.7f},{z:.2f}")
    return " ".join(pts_3d)

# ===============================================================================
# 1. GERAÇÃO DO SALÃO COM TELHADO RETO E ENERGIA SOLAR (COTA REAL SIGSC)
# ===============================================================================
def gerar_kml_salao(sampler):
    c1 = (-49.34689975641707, -27.39563846545191) # NW
    c2 = (-49.34681420669606, -27.39570193199090) # NE
    c4 = (-49.34686676877703, -27.39576267202210) # SE
    c3 = (-49.34694897116752, -27.39569704000664) # SW

    u1 = np.array(to_utm.transform(*c1))
    u2 = np.array(to_utm.transform(*c2))
    u4 = np.array(to_utm.transform(*c4))
    u3 = np.array(to_utm.transform(*c3))

    z1 = sampler(*u1)
    z2 = sampler(*u2)
    z4 = sampler(*u4)
    z3 = sampler(*u3)
    z_floor = float(np.mean([z1, z2, z4, z3])) # ~547.08 m

    h_wall = 3.50
    h_plat = 3.90
    z_laje = z_floor + h_wall
    z_plat = z_floor + h_plat

    v_long = (u2 - u1) / np.linalg.norm(u2 - u1)
    v_short = (u3 - u1) / np.linalg.norm(u3 - u1)
    len_long = np.linalg.norm(u2 - u1)
    len_short = np.linalg.norm(u3 - u1)

    kml = []
    kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    kml.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">')
    kml.append('<Document>')
    kml.append('  <name>Salão com Telhado Reto e Usina de Cobertura (Cota Real SIGSC)</name>')

    kml.append('''
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
  <Style id="estrutura_aluminio">
    <LineStyle><color>ffa0a0a0</color><width>2.0</width></LineStyle>
  </Style>
  <Style id="estilo_pin">
    <IconStyle>
      <scale>1.2</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
      <color>ff00d7ff</color>
    </IconStyle>
  </Style>
''')

    c_center = (c1[0]+c2[0]+c4[0]+c3[0])/4, (c1[1]+c2[1]+c4[1]+c3[1])/4
    kml.append(f'''
  <Placemark>
    <name>UFV Cobertura - Salão Telhado Reto (10,44 kWp) — Cota Real {z_floor:.2f}m</name>
    <styleUrl>#estilo_pin</styleUrl>
    <description><![CDATA[
      <div style="font-family: Arial, sans-serif; min-width: 320px; line-height: 1.5;">
        <h3 style="color: #0b5394; margin-bottom: 8px;">Edificação: Salão com Telhado Reto</h3>
        <p><b>Dimensões da Edificação:</b> 11,00 m × 8,11 m (Área de projeção: ~90,8 m²)</p>
        <p><b>Cota Base Altimétrica (MDT SIGSC):</b> {z_floor:.2f} m acima do nível do mar</p>
        <p><b>Tipo de Telhado:</b> Laje Plana com Platibanda (Telhado Reto)</p>
        <p><b>Pé-direito:</b> 3,50 m (Cota {z_laje:.2f}m) | <b>Platibanda:</b> 3,90 m (Cota {z_plat:.2f}m)</p>
        <hr style="border: 0; border-top: 1px solid #ccc;"/>
        <h4 style="color: #e69138; margin-bottom: 6px;">Sistema Solar Fotovoltaico de Cobertura</h4>
        <ul>
          <li><b>Potência Instalada (DC):</b> 10,44 kWp</li>
          <li><b>Módulos Fotovoltaicos:</b> 18× 580W Bifaciais / TOPCon alta eficiência</li>
          <li><b>Arranjo:</b> 2 fileiras de 9 módulos em orientação norte</li>
          <li><b>Inclinação:</b> 18° voltados ao Norte (estruturas triangulares de alumínio)</li>
          <li><b>Inversor:</b> 1× Inversor Grid-Tie 10 kW Trifásico</li>
          <li><b>Geração Anual Estimada:</b> ~14.200 kWh/ano</li>
        </ul>
      </div>
    ]]></description>
    <Point>
      <altitudeMode>absolute</altitudeMode>
      <coordinates>{c_center[0]:.7f},{c_center[1]:.7f},{z_plat + 1.2:.2f}</coordinates>
    </Point>
  </Placemark>
''')

    # 1. Paredes principais
    walls = [
        (c1, c2, z1, z2),
        (c2, c4, z2, z4),
        (c4, c3, z4, z3),
        (c3, c1, z3, z1)
    ]
    kml.append('  <Folder><name>Estrutura da Edificação (Telhado Reto)</name>')
    for idx, (pa, pb, za, zb) in enumerate(walls):
        kml.append('    <Placemark>')
        kml.append(f'      <name>Parede {idx+1}</name>')
        kml.append('      <styleUrl>#parede</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {pa[0]:.7f},{pa[1]:.7f},{za:.2f} {pb[0]:.7f},{pb[1]:.7f},{zb:.2f} {pb[0]:.7f},{pb[1]:.7f},{z_laje:.2f} {pa[0]:.7f},{pa[1]:.7f},{z_laje:.2f} {pa[0]:.7f},{pa[1]:.7f},{za:.2f}')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')

    # 2. Laje Plana do Telhado
    kml.append('    <Placemark>')
    kml.append('      <name>Laje Plana de Cobertura</name>')
    kml.append('      <styleUrl>#laje</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{z_laje:.2f} {c2[0]:.7f},{c2[1]:.7f},{z_laje:.2f} {c4[0]:.7f},{c4[1]:.7f},{z_laje:.2f} {c3[0]:.7f},{c3[1]:.7f},{z_laje:.2f} {c1[0]:.7f},{c1[1]:.7f},{z_laje:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # 3. Platibanda Perimetral
    kml.append('    <Placemark>')
    kml.append('      <name>Platibanda Perimetral (0,40m)</name>')
    kml.append('      <styleUrl>#platibanda</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{z_laje:.2f} {c2[0]:.7f},{c2[1]:.7f},{z_laje:.2f} {c4[0]:.7f},{c4[1]:.7f},{z_laje:.2f} {c3[0]:.7f},{c3[1]:.7f},{z_laje:.2f} {c1[0]:.7f},{c1[1]:.7f},{z_laje:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')
    for idx, (pa, pb, za, zb) in enumerate(walls):
        kml.append('    <Placemark>')
        kml.append(f'      <name>Platibanda {idx+1}</name>')
        kml.append('      <styleUrl>#platibanda</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {pa[0]:.7f},{pa[1]:.7f},{z_laje:.2f} {pb[0]:.7f},{pb[1]:.7f},{z_laje:.2f} {pb[0]:.7f},{pb[1]:.7f},{z_plat:.2f} {pa[0]:.7f},{pa[1]:.7f},{z_plat:.2f} {pa[0]:.7f},{pa[1]:.7f},{z_laje:.2f}')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')
    kml.append('  </Folder>')

    # 4. Módulos Solares na Laje (18 módulos = 2 fileiras x 9 módulos)
    kml.append('  <Folder><name>Usina Solar de Cobertura (18 Módulos - 10,44 kWp)</name>')
    mod_w = 1.134
    mod_d = 2.278
    tilt_rad = np.radians(18.0)
    d_proj_y = mod_d * np.cos(tilt_rad) # ~2.16m
    z_rise = mod_d * np.sin(tilt_rad)   # ~0.70m

    margin_x = 0.50
    gap_mod = 0.05
    row_pitch_y = 3.60
    z_base_mount = z_laje + 0.15 # 15cm acima da laje

    for row in range(2):
        y_start_u = u1 + (row * row_pitch_y + 1.0) * v_short
        for col in range(9):
            x_start_u = y_start_u + (margin_x + col * (mod_w + gap_mod)) * v_long
            
            p_sw_u = x_start_u
            p_se_u = x_start_u + mod_w * v_long
            # Norte verdadeiro
            p_nw_u = np.array([p_sw_u[0], p_sw_u[1] + d_proj_y])
            p_ne_u = np.array([p_se_u[0], p_se_u[1] + d_proj_y])

            p_sw = to_wgs.transform(*p_sw_u)
            p_se = to_wgs.transform(*p_se_u)
            p_nw = to_wgs.transform(*p_nw_u)
            p_ne = to_wgs.transform(*p_ne_u)

            z_low = z_base_mount
            z_high = z_base_mount + z_rise

            kml.append('    <Placemark>')
            kml.append(f'      <name>Painel R{row+1}-M{col+1}</name>')
            kml.append('      <styleUrl>#painel_solar</styleUrl>')
            kml.append('      <Polygon>')
            kml.append('        <altitudeMode>absolute</altitudeMode>')
            kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
            kml.append(f'          {p_sw[0]:.7f},{p_sw[1]:.7f},{z_low:.2f} {p_se[0]:.7f},{p_se[1]:.7f},{z_low:.2f} {p_ne[0]:.7f},{p_ne[1]:.7f},{z_high:.2f} {p_nw[0]:.7f},{p_nw[1]:.7f},{z_high:.2f} {p_sw[0]:.7f},{p_sw[1]:.7f},{z_low:.2f}')
            kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
            kml.append('      </Polygon>')
            kml.append('    </Placemark>')

            # Suportes triangulares
            kml.append('    <Placemark>')
            kml.append('      <styleUrl>#estrutura_aluminio</styleUrl>')
            kml.append('      <LineString>')
            kml.append('        <altitudeMode>absolute</altitudeMode>')
            kml.append('        <coordinates>')
            kml.append(f'          {p_nw[0]:.7f},{p_nw[1]:.7f},{z_laje:.2f} {p_nw[0]:.7f},{p_nw[1]:.7f},{z_high:.2f} {p_sw[0]:.7f},{p_sw[1]:.7f},{z_low:.2f} {p_sw[0]:.7f},{p_sw[1]:.7f},{z_laje:.2f}')
            kml.append('        </coordinates>')
            kml.append('      </LineString>')
            kml.append('    </Placemark>')

    kml.append('  </Folder>')
    kml.append('</Document>')
    kml.append('</kml>')

    return '\n'.join(kml)

# ===============================================================================
# 2. GERAÇÃO DO PROJETO SOLAR DE SOLO P1, P2 E P3 (COTA REAL SIGSC)
# ===============================================================================
def gerar_kml_setor_solar(poly_wgs84, nome_setor, sampler, table_w=8.0, table_d=4.32, pitch_y=7.5, gap_x=1.5, setback=3.5):
    """
    Gera as mesas solares de solo em 3D, com COTA ABSOLUTA obtida diretamente
    do MDT oficial de 1 metro do SIGSC.
    """
    gdf = gpd.GeoDataFrame([{'geometry': poly_wgs84}], crs='EPSG:4326').to_crs('EPSG:31982')
    geom_utm = gdf.geometry.iloc[0]

    if nome_setor == "P1":
        # Atendimento à solicitação:
        # Retirar 8 mesas de cima (107 a 114) e 5 mesas (20, 21, 34, 35 e 50)
        # e redistribuí-las mantendo as 114 mesas no setor P1.
        excl_zone_top = box(663400, 6968770, 663600, 6968850)
        excl_zone_mid = box(663512, 6968715, 663538, 6968742)
        pitch_y = 6.8
        gap_x = 0.9
        setback = 2.4
        usable = geom_utm.buffer(-setback)
        minx, miny, maxx, maxy = usable.bounds
        tables = []
        y = miny
        while y + table_d <= maxy:
            x = minx
            while x + table_w <= maxx:
                t_box = box(x, y, x + table_w, y + table_d)
                if usable.contains(t_box) and not excl_zone_top.intersects(t_box) and not excl_zone_mid.intersects(t_box):
                    tables.append((x, y))
                x += table_w + gap_x
            y += pitch_y
        tables = tables[:114]
    else:
        usable = geom_utm.buffer(-setback)
        minx, miny, maxx, maxy = usable.bounds
        tables = []
        y = miny
        while y + table_d <= maxy:
            x = minx
            while x + table_w <= maxx:
                t_box = box(x, y, x + table_w, y + table_d)
                if usable.contains(t_box):
                    tables.append((x, y))
                x += table_w + gap_x
            y += pitch_y

    num_tables = len(tables)
    num_modules = num_tables * 14
    dc_power_kwp = num_modules * 0.580
    gen_mwh_ano = dc_power_kwp * 1.520

    kml = []
    kml.append('  <Folder>')
    kml.append(f'    <name>UFV {nome_setor} - {dc_power_kwp:.2f} kWp ({num_tables} mesas / {num_modules} módulos)</name>')

    # Marcador de resumo do setor
    centroid_wgs = to_wgs.transform(geom_utm.centroid.x, geom_utm.centroid.y)
    z_centroid = sampler(geom_utm.centroid.x, geom_utm.centroid.y)
    kml.append(f'''
    <Placemark>
      <name>Ficha Técnica: UFV {nome_setor} — Cota Média {z_centroid:.1f}m</name>
      <styleUrl>#estilo_pin_solo</styleUrl>
      <description><![CDATA[
        <div style="font-family: Arial, sans-serif; min-width: 320px; line-height: 1.5;">
          <h3 style="color: #0b5394; margin-bottom: 8px;">UFV Solo - {nome_setor}</h3>
          <p><b>Área Total do Polígono:</b> {geom_utm.area:,.1f} m² ({(geom_utm.area/10000):.2f} ha)</p>
          <p><b>Cota Altimétrica (MDT SIGSC):</b> ~{z_centroid:.1f} m (Modo: Absolute)</p>
          <hr style="border: 0; border-top: 1px solid #ccc;"/>
          <h4 style="color: #e69138; margin-bottom: 6px;">Dimensionamento Fotovoltaico</h4>
          <ul>
            <li><b>Mesas Fotovoltaicas:</b> {num_tables} mesas (2P × 7 módulos)</li>
            <li><b>Total de Módulos:</b> {num_modules} módulos TOPCon 580W Bifaciais</li>
            <li><b>Potência de Pico (DC):</b> {dc_power_kwp:.2f} kWp</li>
            <li><b>Orientação:</b> Norte Verdadeiro (Azimute 0°) | <b>Inclinação:</b> 20°</li>
            <li><b>Distanciamento Entre Fileiras:</b> {pitch_y:.2f} m (Anti-sombreamento inverno)</li>
            <li><b>Geração Anual Estimada:</b> ~{gen_mwh_ano:,.1f} MWh/ano</li>
          </ul>
        </div>
      ]]></description>
      <Point>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{centroid_wgs[0]:.7f},{centroid_wgs[1]:.7f},{z_centroid + 6.0:.2f}</coordinates>
      </Point>
    </Placemark>
''')

    # Polígono delimitador da área em 3D absoluto
    boundary_3d_str = densificar_fronteira_3d(poly_wgs84, sampler, dz=0.35, step=8.0)
    kml.append(f'''
    <Placemark>
      <name>Limite Perimetral {nome_setor} (Ajustado ao Relevo)</name>
      <styleUrl>#limite_setor</styleUrl>
      <LineString>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{boundary_3d_str}</coordinates>
      </LineString>
    </Placemark>
''')

    # Mesas em 3D Absoluto
    for idx, (tx, ty) in enumerate(tables):
        c_sw_u = (tx, ty)
        c_se_u = (tx + table_w, ty)
        c_ne_u = (tx + table_w, ty + table_d)
        c_nw_u = (tx, ty + table_d)

        c_sw = to_wgs.transform(*c_sw_u)
        c_se = to_wgs.transform(*c_se_u)
        c_ne = to_wgs.transform(*c_ne_u)
        c_nw = to_wgs.transform(*c_nw_u)

        # Cotas reais de solo em cada pé
        zg_sw = sampler(*c_sw_u)
        zg_se = sampler(*c_se_u)
        zg_nw = sampler(*c_nw_u)
        zg_ne = sampler(*c_ne_u)

        # Alturas das bordas do painel
        z_pan_sw = zg_sw + 0.60
        z_pan_se = zg_se + 0.60
        z_pan_nw = zg_nw + 2.15
        z_pan_ne = zg_ne + 2.15

        # Superfície do painel solar fotovoltaico
        kml.append('    <Placemark>')
        kml.append(f'      <name>{nome_setor}-Mesa {idx+1}</name>')
        kml.append('      <styleUrl>#painel_solo</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {c_sw[0]:.7f},{c_sw[1]:.7f},{z_pan_sw:.2f} {c_se[0]:.7f},{c_se[1]:.7f},{z_pan_se:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},{z_pan_ne:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},{z_pan_nw:.2f} {c_sw[0]:.7f},{c_sw[1]:.7f},{z_pan_sw:.2f}')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')

        # Postes estruturais (pernas de aço cravadas no solo real)
        kml.append('    <Placemark>')
        kml.append('      <styleUrl>#perna_solo</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {c_sw[0]:.7f},{c_sw[1]:.7f},{zg_sw:.2f} {c_sw[0]:.7f},{c_sw[1]:.7f},{z_pan_sw:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},{z_pan_nw:.2f} {c_nw[0]:.7f},{c_nw[1]:.7f},{zg_nw:.2f}')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')
        kml.append('    <Placemark>')
        kml.append('      <styleUrl>#perna_solo</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {c_se[0]:.7f},{c_se[1]:.7f},{zg_se:.2f} {c_se[0]:.7f},{c_se[1]:.7f},{z_pan_se:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},{z_pan_ne:.2f} {c_ne[0]:.7f},{c_ne[1]:.7f},{zg_ne:.2f}')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')

    kml.append('  </Folder>')
    return '\n'.join(kml), num_tables, num_modules, dc_power_kwp, gen_mwh_ano

# ===============================================================================
# 3. ROTINA PRINCIPAL DE INTEGRAÇÃO
# ===============================================================================
def main():
    print("Iniciando reprojeção altimétrica absoluta dos projetos...")
    sampler = get_mdt_sampler()

    poly_sitio = parse_kmz_polygon(os.path.join(SOLAR_DIR, "Novo_sitio_das_andorinhas.kmz"))
    poly_p1 = parse_kmz_polygon(os.path.join(SOLAR_DIR, "p1.kmz"))
    poly_p2 = parse_kmz_polygon(os.path.join(SOLAR_DIR, "p2.kmz"))
    poly_p3 = parse_kmz_polygon(os.path.join(SOLAR_DIR, "p3.kmz"))

    # 1. Salão Telhado Reto
    kml_salao = gerar_kml_salao(sampler)
    salao_kmz = os.path.join(SOLAR_DIR, "salao_telhado_reto_com_solar.kmz")
    with zipfile.ZipFile(salao_kmz, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', kml_salao.encode('utf-8'))
    print(f"Salão com telhado reto e solar gerado: {salao_kmz}")

    salao_orig_kmz = os.path.join(SOLAR_DIR, "salao_telhado_reto (2).kmz")
    with zipfile.ZipFile(salao_orig_kmz, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', kml_salao.encode('utf-8'))

    # 2. Gerar Setores P1, P2 e P3
    kml_p1, t1, m1, kw1, gen1 = gerar_kml_setor_solar(poly_p1, "P1", sampler)
    kml_p2, t2, m2, kw2, gen2 = gerar_kml_setor_solar(poly_p2, "P2", sampler, setback=3.5)
    kml_p3, t3, m3, kw3, gen3 = gerar_kml_setor_solar(poly_p3, "P3", sampler, setback=3.5)

    tot_tables = t1 + t2 + t3
    tot_modules = m1 + m2 + m3
    tot_dc_kwp = kw1 + kw2 + kw3
    tot_gen_mwh = gen1 + gen2 + gen3

    styles_header = '''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <Style id="painel_solo">
    <LineStyle><color>ffa0a0a0</color><width>1.0</width></LineStyle>
    <PolyStyle><color>ffd55018</color></PolyStyle>
  </Style>
  <Style id="perna_solo">
    <LineStyle><color>ff888888</color><width>1.8</width></LineStyle>
  </Style>
  <Style id="limite_setor">
    <LineStyle><color>ff0000ff</color><width>2.5</width></LineStyle>
  </Style>
  <Style id="estilo_pin_solo">
    <IconStyle>
      <scale>1.3</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
      <color>ff11ccff</color>
    </IconStyle>
  </Style>
'''
    for name, content in [('projeto_solar_p1.kmz', kml_p1), ('projeto_solar_p2.kmz', kml_p2), ('projeto_solar_p3.kmz', kml_p3)]:
        kmz_path = os.path.join(SOLAR_DIR, name)
        full_kml = styles_header + content + '\n</Document>\n</kml>'
        with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as z:
            z.writestr('doc.kml', full_kml.encode('utf-8'))
        print(f"KMZ individual gerado: {kmz_path}")

    # ===============================================================================
    # 4. MASTER PROJECT UNIFICADO
    # ===============================================================================
    sitio_3d_str = densificar_fronteira_3d(poly_sitio, sampler, dz=0.45, step=10.0)

    master_kml = []
    master_kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    master_kml.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">')
    master_kml.append('<Document>')
    master_kml.append('  <name>Projeto Solar Completo - Sítio das Andorinhas</name>')
    master_kml.append('  <open>1</open>')

    master_kml.append('''
  <Style id="limite_sitio">
    <LineStyle><color>ffffaa00</color><width>3.5</width></LineStyle>
  </Style>
  <Style id="limite_setor">
    <LineStyle><color>ff0055ff</color><width>2.5</width></LineStyle>
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
  <Style id="estrutura_aluminio">
    <LineStyle><color>ffa0a0a0</color><width>2.0</width></LineStyle>
  </Style>
  <Style id="painel_info">
    <IconStyle>
      <scale>1.6</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/star.png</href></Icon>
      <color>ff00ffff</color>
    </IconStyle>
  </Style>
''')

    # Marcador Executivo Geral
    z_exec = sampler(663468.0, 6968640.0)
    master_kml.append(f'''
  <Placemark>
    <name>★★ PAINEL EXECUTIVO: SÍTIO DAS ANDORINHAS ★★</name>
    <styleUrl>#painel_info</styleUrl>
    <description><![CDATA[
      <div style="font-family: Arial, sans-serif; min-width: 440px; line-height: 1.5;">
        <h2 style="color: #0b5394; margin-bottom: 4px;">Complexo Sustentável Sítio das Andorinhas</h2>
        <p style="color: #555; margin-top: 0;"><b>Localização:</b> Estrada Ribeirão dos Ovos, Vidal Ramos - SC | <b>Área Total:</b> 18,60 hectares</p>
        <p style="background: #eef5ff; padding: 6px; border-left: 4px solid #0b5394;"><b>Georreferenciamento de Alta Precisão:</b> Todas as cotas e superfícies foram calibradas em modo <b>altitudeMode: absolute</b> sobre o Modelo Digital de Terreno (MDT) de 1 metro e Ortofoto de 0,39m da SDS/SDC (SIGSC).</p>
        <hr style="border: 0; border-top: 1px solid #ccc;"/>
        
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <tr style="background-color: #0b5394; color: white;">
            <th style="padding: 6px; border: 1px solid #999;">Setor da Usina</th>
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
      <altitudeMode>absolute</altitudeMode>
      <coordinates>-49.3468500,-27.3957000,{z_exec + 10.0:.2f}</coordinates>
    </Point>
  </Placemark>
''')

    # Camada 1: Base Cartográfica Oficial de Santa Catarina - SIGSC (SDS/SDC)
    master_kml.append('''
  <Folder>
    <name>Base Cartográfica Oficial de Santa Catarina - SIGSC (SDS/SDC)</name>
    <NetworkLink>
      <name>Modelo 3D Real Texturizado com a Ortofoto Oficial (MDT 1m + Ortofoto 0,39m)</name>
      <visibility>1</visibility>
      <open>0</open>
      <Link>
        <href>MDT_3D_Sitio_das_Andorinhas.kmz</href>
      </Link>
    </NetworkLink>
    <NetworkLink>
      <name>Curvas de Nível Topográficas Equidistância 5m (SIGSC)</name>
      <visibility>1</visibility>
      <open>0</open>
      <Link>
        <href>MDT_Curvas_de_Nivel.kmz</href>
      </Link>
    </NetworkLink>
    <NetworkLink>
      <name>Ortofoto Oficial do Estado 2D (Folha SG-22-Z-D-I-3-SE-A)</name>
      <visibility>0</visibility>
      <open>0</open>
      <Link>
        <href>Ortofoto_SIGSC_Sitio_das_Andorinhas.kmz</href>
      </Link>
    </NetworkLink>
  </Folder>
''')

    # Camada 2: Levantamento por Drone
    master_kml.append('''
  <Folder>
    <name>Levantamentos Aerofotogramétricos por Drone</name>
    <NetworkLink>
      <name>Ortofoto de Drone Detalhada (01/03/2026)</name>
      <visibility>1</visibility>
      <open>0</open>
      <Link>
        <href>Estrada-Ribeiro-dos-Ovos-01-03-2026-orthophoto.kmz</href>
        <viewRefreshMode>onRegion</viewRefreshMode>
      </Link>
    </NetworkLink>
    <NetworkLink>
      <name>Trajetórias de Voo e Câmeras Drone (2.161 fotos 2026)</name>
      <visibility>0</visibility>
      <open>0</open>
      <Link>
        <href>Voo_Drone_2026_Sitio_das_Andorinhas.kmz</href>
      </Link>
    </NetworkLink>
    <NetworkLink>
      <name>Ortofoto de Drone Anterior (01/06/2024)</name>
      <visibility>0</visibility>
      <open>0</open>
      <Link>
        <href>Estrada-Ribeiro-dos-Ovos-01-06-2024-orthophoto_1.kmz</href>
        <viewRefreshMode>onRegion</viewRefreshMode>
      </Link>
    </NetworkLink>
  </Folder>
''')

    # Camada 3: Limite Perimetral do Sítio
    master_kml.append(f'''
  <Placemark>
    <name>Limite do Sítio das Andorinhas (18,60 ha - Cota Real)</name>
    <styleUrl>#limite_sitio</styleUrl>
    <LineString>
      <altitudeMode>absolute</altitudeMode>
      <coordinates>{sitio_3d_str}</coordinates>
    </LineString>
  </Placemark>
''')

    # Camada 4: Salão com Telhado Reto e Usina Rooftop
    salao_inner = kml_salao[kml_salao.find('<Placemark>'):kml_salao.rfind('</Document>')]
    master_kml.append('  <Folder>')
    master_kml.append('    <name>Salão com Telhado Reto e Usina de Cobertura (10,44 kWp)</name>')
    master_kml.append(salao_inner)
    master_kml.append('  </Folder>')

    # Camada 5: Campo de Areia com Redes 3D
    from gerar_campo_de_areia_3d import gerar_campo_areia_kml
    kml_campo = gerar_campo_areia_kml()
    campo_inner = kml_campo[kml_campo.find('<Placemark>'):kml_campo.rfind('</Document>')]
    master_kml.append('  <Folder>')
    master_kml.append('    <name>Campo de Futebol e Vôlei de Areia (Redes 3D)</name>')
    master_kml.append(campo_inner)
    master_kml.append('  </Folder>')

    # Camada 6: Usinas de Solo P1, P2 e P3
    master_kml.append('  <Folder>')
    master_kml.append(f'    <name>Usina Solar Solo - Complexo P1, P2 e P3 ({tot_dc_kwp:.2f} kWp)</name>')
    master_kml.append(kml_p1)
    master_kml.append(kml_p2)
    master_kml.append(kml_p3)
    master_kml.append('  </Folder>')

    master_kml.append('</Document>')
    master_kml.append('</kml>')

    master_kmz_path = os.path.join(SOLAR_DIR, "Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz")
    with zipfile.ZipFile(master_kmz_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', '\n'.join(master_kml).encode('utf-8'))

    print(f"MASTER KMZ GERADO COM SUCESSO: {master_kmz_path}")
    print("="*70)
    print(f"RESUMO FINAL COM REPROJEÇÃO ALTIMÉTRICA ABSOLUTA:")
    print(f"  • MDT 3D COLLADA texturizado com Ortofoto SIGSC 0,39m: MDT_3D_Sitio_das_Andorinhas.kmz")
    print(f"  • Modo de Altitude: ABSOLUTE calibrado sobre MDT 1,0 m do SIGSC em todos os projetos")
    print(f"  • Campo de Areia 3D: Cota base {sampler(663468.0, 6968640.0):.2f} m, redes a 6,00 m")
    print(f"  • Salão Telhado Reto: Cota base ~547.08 m, laje a 550.58 m, platibanda a 550.98 m")
    print(f"  • Setor Solo P1: {t1} mesas, {m1} módulos = {kw1:.2f} kWp (redistribuído)")
    print(f"  • Setor Solo P2: {t2} mesas, {m2} módulos = {kw2:.2f} kWp")
    print(f"  • Setor Solo P3: {t3} mesas, {m3} módulos = {kw3:.2f} kWp")
    print(f"  • Total Usina Solar: {tot_modules + 18:,} módulos = {(tot_dc_kwp + 10.44):,.2f} kWp (~1,90 MWp)")
    print(f"  • Master KMZ: {master_kmz_path}")
    print("="*70)

if __name__ == '__main__':
    main()
