#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o modelo 3D do Campo de Futebol / Vôlei de Areia do Mar em KML/KMZ:
- Cota altimétrica métrica REAL do MDT 1,0 m do SIGSC (altitudeMode: absolute)
- Caixa de areia do mar: 22,0 m × 12,0 m
- Guia de contenção perimetral
- Marcação oficial de vôlei / futevôlei (16,0 m × 8,0 m)
- Rede central com mastros (altura 2,43 m)
- Traves de beach soccer nas duas cabeceiras (3,0 m × 2,0 m)
- Estrutura de postes tubulares em aço galvanizado (altura 6,00 m)
- Redes de proteção perimetrais (altura 6,00 m)
- Rede de proteção superior / teto anti-fuga de bola (a 6,00 m de altura) com cabos de aço
- Refletores LED nos 4 cantos
"""

import os
import zipfile
import rasterio
import numpy as np
from pyproj import Transformer

to_utm = Transformer.from_crs('EPSG:4326', 'EPSG:31982', always_xy=True)
to_wgs = Transformer.from_crs('EPSG:31982', 'EPSG:4326', always_xy=True)

SOLAR_DIR = r"C:\Users\haas\github\solar"
MDT_PATH = os.path.join(SOLAR_DIR, "MDT_Novo_sitio_das_andorinhas.tif")

def get_mdt_sampler():
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
        return val if val != nodata and not np.isnan(val) else 547.56

    return sample

def gerar_campo_areia_kml():
    sampler = get_mdt_sampler()

    # Ponto central indicado em Campo_de_areia.kml
    lon_c, lat_c = -49.34668483068334, -27.39581155062853
    cx, cy = to_utm.transform(lon_c, lat_c)
    center = np.array([cx, cy])

    # Cota real do solo no centro do campo pelo MDT 1m SIGSC
    z_base = sampler(cx, cy) # ~547.56 m

    # Orientação paralela à estrada / terraço (~118° de azimute)
    az_rad = np.radians(118.0)
    v_l = np.array([np.sin(az_rad), np.cos(az_rad)])   # vetor longitudinal (comprimento)
    v_w = np.array([-np.cos(az_rad), np.sin(az_rad)])  # vetor transversal (largura)

    L = 22.0  # Comprimento total da caixa de areia
    W = 12.0  # Largura total da caixa de areia
    H_net = 6.00  # Altura das redes de proteção (perímetro e teto)
    z_top = z_base + H_net

    # 4 cantos da caixa de areia no solo
    c1_u = center - (L/2)*v_l - (W/2)*v_w
    c2_u = center + (L/2)*v_l - (W/2)*v_w
    c3_u = center + (L/2)*v_l + (W/2)*v_w
    c4_u = center - (L/2)*v_l + (W/2)*v_w

    c1 = to_wgs.transform(*c1_u)
    c2 = to_wgs.transform(*c2_u)
    c3 = to_wgs.transform(*c3_u)
    c4 = to_wgs.transform(*c4_u)

    kml = []
    kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    kml.append('<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">')
    kml.append('<Document>')
    kml.append('  <name>Campo de Futebol e Vôlei de Areia com Redes 3D (Cota Real SIGSC)</name>')

    # Estilos
    kml.append('''
  <Style id="areia_mar">
    <LineStyle><color>ff88aa99</color><width>2.0</width></LineStyle>
    <PolyStyle><color>ffe0efff</color></PolyStyle>
  </Style>
  <Style id="rede_lateral">
    <LineStyle><color>88ffffff</color><width>1.0</width></LineStyle>
    <PolyStyle><color>55222222</color></PolyStyle>
  </Style>
  <Style id="rede_teto">
    <LineStyle><color>66aaaaaa</color><width>1.0</width></LineStyle>
    <PolyStyle><color>40333333</color></PolyStyle>
  </Style>
  <Style id="poste_aco">
    <LineStyle><color>ffd0d0d0</color><width>3.5</width></LineStyle>
  </Style>
  <Style id="cabo_aco">
    <LineStyle><color>ff888888</color><width>1.5</width></LineStyle>
  </Style>
  <Style id="rede_volei">
    <LineStyle><color>ffffffff</color><width>1.8</width></LineStyle>
    <PolyStyle><color>ccffffff</color></PolyStyle>
  </Style>
  <Style id="trave_gol">
    <LineStyle><color>ffffffff</color><width>3.0</width></LineStyle>
  </Style>
  <Style id="linha_jogo">
    <LineStyle><color>ffff3300</color><width>2.5</width></LineStyle>
  </Style>
  <Style id="pin_esporte">
    <IconStyle>
      <scale>1.3</scale>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/sports.png</href></Icon>
      <color>ff00ffaa</color>
    </IconStyle>
  </Style>
''')

    # Ficha Técnica
    kml.append(f'''
  <Placemark>
    <name>Campo de Areia do Mar (22m × 12m) — Cota Real {z_base:.2f}m</name>
    <styleUrl>#pin_esporte</styleUrl>
    <description><![CDATA[
      <div style="font-family: Arial, sans-serif; min-width: 320px; line-height: 1.5;">
        <h3 style="color: #0b5394; margin-bottom: 6px;">Complexo Esportivo: Arena de Areia do Mar</h3>
        <p><b>Dimensões da Caixa de Areia:</b> 22,00 m × 12,00 m (Área: 264,0 m²)</p>
        <p><b>Cota Base Altimétrica (MDT SIGSC):</b> {z_base:.2f} m acima do nível do mar</p>
        <p><b>Material da Quadra:</b> Areia do mar tratada, drenante e higienizada</p>
        <p><b>Estrutura de Fechamento Integral:</b></p>
        <ul>
          <li><b>Redes Perimetrais (ao redor):</b> Altura 6,00 m em malha de polietileno trançado 10×10 cm de alta tenacidade com proteção UV.</li>
          <li><b>Rede Superior (acima / teto):</b> Cobertura total anti-fuga a 6,00 m de altura (Cota {z_top:.2f}m), sustentada por cabos de aço galvanizados.</li>
          <li><b>Sustentação:</b> 10 postes tubulares metálicos galvanizados a fogo.</li>
          <li><b>Modalidades Atendidas:</b> Futebol de Areia / Beach Soccer, Vôlei de Praia, Futevôlei e Beach Tennis.</li>
          <li><b>Equipamentos:</b> Rede central oficial com mastros, traves tubulares brancas de futebol de areia e linhas demarcatórias azuis (16m × 8m).</li>
        </ul>
      </div>
    ]]></description>
    <Point>
      <altitudeMode>absolute</altitudeMode>
      <coordinates>{lon_c:.7f},{lat_c:.7f},{z_top + 1.0:.2f}</coordinates>
    </Point>
  </Placemark>
''')

    # 1. Caixa de Areia (Superfície)
    z_sand = z_base + 0.08
    kml.append('  <Folder><name>Caixa de Areia e Marcações</name>')
    kml.append('    <Placemark>')
    kml.append('      <name>Piso de Areia do Mar</name>')
    kml.append('      <styleUrl>#areia_mar</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{z_sand:.2f} {c2[0]:.7f},{c2[1]:.7f},{z_sand:.2f} {c3[0]:.7f},{c3[1]:.7f},{z_sand:.2f} {c4[0]:.7f},{c4[1]:.7f},{z_sand:.2f} {c1[0]:.7f},{c1[1]:.7f},{z_sand:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Linhas de jogo oficiais (16m x 8m no centro da caixa)
    j_L, j_W = 16.0, 8.0
    j1_u = center - (j_L/2)*v_l - (j_W/2)*v_w
    j2_u = center + (j_L/2)*v_l - (j_W/2)*v_w
    j3_u = center + (j_L/2)*v_l + (j_W/2)*v_w
    j4_u = center - (j_L/2)*v_l + (j_W/2)*v_w

    j1 = to_wgs.transform(*j1_u)
    j2 = to_wgs.transform(*j2_u)
    j3 = to_wgs.transform(*j3_u)
    j4 = to_wgs.transform(*j4_u)
    z_line = z_sand + 0.04

    kml.append('    <Placemark>')
    kml.append('      <name>Linhas de Jogo (16m x 8m)</name>')
    kml.append('      <styleUrl>#linha_jogo</styleUrl>')
    kml.append('      <LineString>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <coordinates>')
    kml.append(f'          {j1[0]:.7f},{j1[1]:.7f},{z_line:.2f} {j2[0]:.7f},{j2[1]:.7f},{z_line:.2f} {j3[0]:.7f},{j3[1]:.7f},{z_line:.2f} {j4[0]:.7f},{j4[1]:.7f},{z_line:.2f} {j1[0]:.7f},{j1[1]:.7f},{z_line:.2f}')
    kml.append('        </coordinates>')
    kml.append('      </LineString>')
    kml.append('    </Placemark>')

    # Rede central de Vôlei / Beach Tennis
    net_s_u = center - (W/2)*v_w
    net_n_u = center + (W/2)*v_w
    net_s = to_wgs.transform(*net_s_u)
    net_n = to_wgs.transform(*net_n_u)

    kml.append('    <Placemark>')
    kml.append('      <name>Rede Central de Vôlei / Beach Tennis</name>')
    kml.append('      <styleUrl>#rede_volei</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {net_s[0]:.7f},{net_s[1]:.7f},{z_base + 1.00:.2f} {net_n[0]:.7f},{net_n[1]:.7f},{z_base + 1.00:.2f} {net_n[0]:.7f},{net_n[1]:.7f},{z_base + 2.43:.2f} {net_s[0]:.7f},{net_s[1]:.7f},{z_base + 2.43:.2f} {net_s[0]:.7f},{net_s[1]:.7f},{z_base + 1.00:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Traves de futebol nas extremidades (largura 3m, altura 2m)
    for end_idx, sign in enumerate([-1, 1]):
        goal_c_u = center + sign * (L/2 - 0.5) * v_l
        g_l_u = goal_c_u - 1.5 * v_w
        g_r_u = goal_c_u + 1.5 * v_w
        gl = to_wgs.transform(*g_l_u)
        gr = to_wgs.transform(*g_r_u)
        kml.append(f'    <Placemark>')
        kml.append(f'      <name>Trave de Futebol {end_idx+1}</name>')
        kml.append('      <styleUrl>#trave_gol</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {gl[0]:.7f},{gl[1]:.7f},{z_base:.2f} {gl[0]:.7f},{gl[1]:.7f},{z_base + 2.00:.2f} {gr[0]:.7f},{gr[1]:.7f},{z_base + 2.00:.2f} {gr[0]:.7f},{gr[1]:.7f},{z_base:.2f}')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')
    kml.append('  </Folder>')

    # 2. Redes de Proteção ao Redor (Perímetro 6,00 m de altura)
    kml.append('  <Folder><name>Redes de Proteção Perimetrais (ao redor - 6m)</name>')
    perimeter_sides = [
        ("Lado Sul (Estrada)", c1, c2, c1_u, c2_u),
        ("Lado Leste (Fundo)", c2, c3, c2_u, c3_u),
        ("Lado Norte (Mata)", c3, c4, c3_u, c4_u),
        ("Lado Oeste (Salão)", c4, c1, c4_u, c1_u)
    ]
    for s_name, pa, pb, pa_u, pb_u in perimeter_sides:
        za = sampler(pa_u[0], pa_u[1])
        zb = sampler(pb_u[0], pb_u[1])
        kml.append('    <Placemark>')
        kml.append(f'      <name>Rede {s_name}</name>')
        kml.append('      <styleUrl>#rede_lateral</styleUrl>')
        kml.append('      <Polygon>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
        kml.append(f'          {pa[0]:.7f},{pa[1]:.7f},{za:.2f} {pb[0]:.7f},{pb[1]:.7f},{zb:.2f} {pb[0]:.7f},{pb[1]:.7f},{z_top:.2f} {pa[0]:.7f},{pa[1]:.7f},{z_top:.2f} {pa[0]:.7f},{pa[1]:.7f},{za:.2f}')
        kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
        kml.append('      </Polygon>')
        kml.append('    </Placemark>')
    kml.append('  </Folder>')

    # 3. Postes de Sustentação em Aço Galvanizado (ao redor)
    kml.append('  <Folder><name>Postes Metálicos Estruturais (6m)</name>')
    post_positions_u = [
        c1_u,
        c1_u + (L/3)*v_l,
        c1_u + (2*L/3)*v_l,
        c2_u,
        (c2_u + c3_u)/2,
        c3_u,
        c4_u + (2*L/3)*v_l,
        c4_u + (L/3)*v_l,
        c4_u,
        (c1_u + c4_u)/2
    ]
    for p_idx, pu in enumerate(post_positions_u):
        pw = to_wgs.transform(*pu)
        zp_ground = sampler(pu[0], pu[1])
        kml.append('    <Placemark>')
        kml.append(f'      <name>Poste {p_idx+1}</name>')
        kml.append('      <styleUrl>#poste_aco</styleUrl>')
        kml.append('      <LineString>')
        kml.append('        <altitudeMode>absolute</altitudeMode>')
        kml.append('        <coordinates>')
        kml.append(f'          {pw[0]:.7f},{pw[1]:.7f},{zp_ground:.2f} {pw[0]:.7f},{pw[1]:.7f},{z_top:.2f}')
        kml.append('        </coordinates>')
        kml.append('      </LineString>')
        kml.append('    </Placemark>')
    kml.append('  </Folder>')

    # 4. Rede de Proteção Superior / Teto (acima a 6,00 m)
    kml.append('  <Folder><name>Rede de Proteção Superior (acima / teto anti-fuga)</name>')
    kml.append('    <Placemark>')
    kml.append('      <name>Rede Superior de Cobertura (Teto 6,00m)</name>')
    kml.append('      <styleUrl>#rede_teto</styleUrl>')
    kml.append('      <Polygon>')
    kml.append('        <altitudeMode>absolute</altitudeMode>')
    kml.append('        <outerBoundaryIs><LinearRing><coordinates>')
    kml.append(f'          {c1[0]:.7f},{c1[1]:.7f},{z_top:.2f} {c2[0]:.7f},{c2[1]:.7f},{z_top:.2f} {c3[0]:.7f},{c3[1]:.7f},{z_top:.2f} {c4[0]:.7f},{c4[1]:.7f},{z_top:.2f} {c1[0]:.7f},{c1[1]:.7f},{z_top:.2f}')
    kml.append('        </coordinates></LinearRing></outerBoundaryIs>')
    kml.append('      </Polygon>')
    kml.append('    </Placemark>')

    # Cabos de aço de reforço estrutural (X diagonal + travessas)
    kml.append('    <Placemark>')
    kml.append('      <name>Cabos de Aço de Travamento Superior</name>')
    kml.append('      <styleUrl>#cabo_aco</styleUrl>')
    kml.append('      <MultiGeometry>')
    kml.append(f'        <LineString><altitudeMode>absolute</altitudeMode><coordinates>{c1[0]:.7f},{c1[1]:.7f},{z_top:.2f} {c3[0]:.7f},{c3[1]:.7f},{z_top:.2f}</coordinates></LineString>')
    kml.append(f'        <LineString><altitudeMode>absolute</altitudeMode><coordinates>{c2[0]:.7f},{c2[1]:.7f},{z_top:.2f} {c4[0]:.7f},{c4[1]:.7f},{z_top:.2f}</coordinates></LineString>')
    kml.append(f'        <LineString><altitudeMode>absolute</altitudeMode><coordinates>{net_s[0]:.7f},{net_s[1]:.7f},{z_top:.2f} {net_n[0]:.7f},{net_n[1]:.7f},{z_top:.2f}</coordinates></LineString>')
    kml.append('      </MultiGeometry>')
    kml.append('    </Placemark>')
    kml.append('  </Folder>')

    kml.append('</Document>')
    kml.append('</kml>')

    return '\n'.join(kml)

if __name__ == '__main__':
    kml_str = gerar_campo_areia_kml()
    out_kmz = os.path.join(SOLAR_DIR, "Campo_de_areia_modelado_com_redes.kmz")
    with zipfile.ZipFile(out_kmz, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', kml_str.encode('utf-8'))
    print(f"Gerado Campo de Areia com Redes 3D (Cota Real SIGSC): {out_kmz}")

    out_kml = os.path.join(SOLAR_DIR, "Campo_Areia_Modelado.kml")
    with open(out_kml, 'w', encoding='utf-8') as f:
        f.write(kml_str)
