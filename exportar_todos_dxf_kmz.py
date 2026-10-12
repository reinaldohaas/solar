#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exporta todas as edificações e estruturas do Sítio das Andorinhas para CAD (DXF) e Google Earth (KMZ):
1. Casa do Sítio (200 m², cumeeira compartilhada, telhado 1 oeste, telhado 2 leste, paredes e piso)
2. Salão de Festas (12×8m = 96 m², 6 pilares, cobertura 2 águas e usina solar com 36 módulos)
3. Quadra de Areia (22×12m, borda, postes, telas de proteção Sul, Leste e Norte H=6m, lado Oeste aberto)
4. Chalés 1 a 5 (22 m² cada, pilotis no terreno natural, deck, varanda, cobertura e giro dos chalés 4 e 5 para a Casa)

Gera:
- Arquivo mestre unificado: Projeto_Completo_Sitio_Edificacoes.dxf e Projeto_Completo_Sitio_Edificacoes.kmz
- Arquivos individuais separados em DXF e KMZ para cada elemento
"""

import os
import math
import zipfile
import xml.etree.ElementTree as ET
import ezdxf
from ezdxf import units
from pyproj import Transformer

SOLAR_DIR = r"C:\Users\haas\github\solar"
transformer = Transformer.from_crs("EPSG:31982", "EPSG:4326", always_xy=True)

def utm_to_wgs84(e, n):
    lon, lat = transformer.transform(e, n)
    return lon, lat

def local_to_utm(lx, lz, base_e, base_n, rot_rad):
    # Rotação em torno do eixo Y (plano XZ horizontal)
    # No modelo Three.js: X aponta a Leste (quando rot=0), Z aponta a Sul (-Norte)
    cos_r = math.cos(rot_rad)
    sin_r = math.sin(rot_rad)
    rx = lx * cos_r + lz * sin_r
    rz = -lx * sin_r + lz * cos_r
    e = base_e + rx
    n = base_n - rz
    return e, n

# ==============================================================================
# 1. DADOS GEOMÉTRICOS EXATOS
# ==============================================================================

# A) CASA DO SÍTIO
CASA_BASE_UTM = (663415.50, 6968636.50)
COTA_CASA = 540.95
H_RIDGE = 4.60
S_WEST = 0.34
S_EAST = 0.235

RS = (663412.325, 6968630.679)
RN = (663415.673, 6968642.764)
UE = 0.266982
UN = 0.963702
NE = 0.963702
NN = -0.266982

def get_casa_roof_point(e, n):
    perp = (e - RS[0]) * NE + (n - RS[1]) * NN
    h = (H_RIDGE - S_WEST * abs(perp)) if perp <= 0 else (H_RIDGE - S_EAST * perp)
    return (e, n, COTA_CASA + h)

T1_UTM_2D = [
    (663408.675, 6968631.318),
    RS,
    RN,
    (663411.758, 6968643.518),
    (663408.972, 6968633.456),
    (663407.240, 6968633.914)
]
T1_3D = [get_casa_roof_point(e, n) for e, n in T1_UTM_2D]

T2_UTM_2D = [
    RS,
    (663420.916, 6968628.307),
    (663424.264, 6968640.392),
    RN
]
T2_3D = [get_casa_roof_point(e, n) for e, n in T2_UTM_2D]

# Paredes da Casa (polígono perimetral sob o beiral)
CASA_WALL_UTM_2D = [
    (663408.20, 6968632.00),
    (663412.32, 6968630.80),
    (663420.50, 6968628.60),
    (663423.80, 6968640.10),
    (663415.40, 6968642.40),
    (663411.50, 6968643.20),
    (663408.70, 6968633.60),
    (663407.50, 6968634.00)
]

# B) SALÃO DE FESTAS (12m x 8m)
SALAO_BASE_UTM = (663445.60, 6968642.80)
COTA_SALAO = 547.10
SALAO_ROT_RAD = -0.489038 # -28.02°

# C) QUADRA DE AREIA (22m x 12m)
QUADRA_BASE_UTM = (663456.88, 6968636.85)
COTA_QUADRA = 547.25
QUADRA_ROT_RAD = -0.489038

# D) CHALÉS 1 A 5 (22 m² cada - 5.50m x 4.00m)
CHALES = [
    {"id": 1, "utm": (663457.29, 6968674.96), "cota": 551.91, "rot": SALAO_ROT_RAD},
    {"id": 2, "utm": (663448.54, 6968667.08), "cota": 549.73, "rot": SALAO_ROT_RAD},
    {"id": 3, "utm": (663438.93, 6968659.26), "cota": 547.07, "rot": SALAO_ROT_RAD},
    {"id": 4, "utm": (663466.65, 6968618.00), "cota": 549.02, "rot": math.atan2(CASA_BASE_UTM[0] - 663466.65, -(CASA_BASE_UTM[1] - 6968618.00))},
    {"id": 5, "utm": (663469.69, 6968600.54), "cota": 549.40, "rot": math.atan2(CASA_BASE_UTM[0] - 663469.69, -(CASA_BASE_UTM[1] - 6968600.54))}
]

# ==============================================================================
# 2. GERADORES DE ELEMENTOS GEOMÉTRICOS (DXF E KMZ)
# ==============================================================================

def add_dxf_box_mesh(msp, center_e, center_n, base_z, length_x, width_z, height_y, rot_rad, layer):
    """Cria uma caixa 3D sólida orientada no DXF"""
    hx = length_x / 2.0
    hz = width_z / 2.0
    z0 = base_z
    z1 = base_z + height_y
    
    corners_local = [
        (-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)
    ]
    corners_utm = [local_to_utm(lx, lz, center_e, center_n, rot_rad) for lx, lz in corners_local]
    b = [(e, n, z0) for e, n in corners_utm]
    t = [(e, n, z1) for e, n in corners_utm]
    
    # 6 Faces (3DFace)
    msp.add_3dface([b[0], b[1], b[2], b[3]], dxfattribs={'layer': layer})
    msp.add_3dface([t[3], t[2], t[1], t[0]], dxfattribs={'layer': layer})
    msp.add_3dface([b[0], b[1], t[1], t[0]], dxfattribs={'layer': layer})
    msp.add_3dface([b[1], b[2], t[2], t[1]], dxfattribs={'layer': layer})
    msp.add_3dface([b[2], b[3], t[3], t[2]], dxfattribs={'layer': layer})
    msp.add_3dface([b[3], b[0], t[0], t[3]], dxfattribs={'layer': layer})

def add_dxf_quad(msp, p1, p2, p3, p4, layer):
    msp.add_3dface([p1, p2, p3, p4], dxfattribs={'layer': layer})

def add_dxf_polyline3d(msp, points, layer, closed=False):
    msp.add_polyline3d(points, dxfattribs={'layer': layer, 'flags': 1 if closed else 0})

# KML Helpers
def kml_coords_str(pts_3d):
    tokens = []
    for p in pts_3d:
        lon, lat = utm_to_wgs84(p[0], p[1])
        tokens.append(f"{lon:.8f},{lat:.8f},{p[2]:.2f}")
    return " ".join(tokens)

def create_kml_polygon(name, pts_3d, color_hex="ffffffff", fill=1, outline=1):
    pts_closed = list(pts_3d)
    if pts_closed[0] != pts_closed[-1]:
        pts_closed.append(pts_closed[0])
    c_str = kml_coords_str(pts_closed)
    esc_name = str(name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <Placemark>
      <name>{esc_name}</name>
      <Style>
        <LineStyle><color>{color_hex}</color><width>2</width></LineStyle>
        <PolyStyle><color>{color_hex}</color><fill>{fill}</fill><outline>{outline}</outline></PolyStyle>
      </Style>
      <Polygon>
        <altitudeMode>absolute</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>{c_str}</coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>"""

def create_kml_linestring(name, pts_3d, color_hex="ff00ffff", width=3):
    c_str = kml_coords_str(pts_3d)
    esc_name = str(name).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""
    <Placemark>
      <name>{esc_name}</name>
      <Style>
        <LineStyle><color>{color_hex}</color><width>{width}</width></LineStyle>
      </Style>
      <LineString>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{c_str}</coordinates>
      </LineString>
    </Placemark>"""

# ==============================================================================
# 3. CONSTRUTORES DE CADA EDIFICAÇÃO
# ==============================================================================

def export_casa(doc=None, kml_elements=None):
    """Exporta Casa do Sítio"""
    if doc is not None:
        msp = doc.modelspace()
        # Cumeeira
        rs3 = (RS[0], RS[1], COTA_CASA + H_RIDGE)
        rn3 = (RN[0], RN[1], COTA_CASA + H_RIDGE)
        add_dxf_polyline3d(msp, [rs3, rn3], 'CASA_CUMEEIRA')
        
        # Telhado 1 (Ala Oeste)
        for i in range(1, len(T1_3D) - 1):
            add_dxf_quad(msp, T1_3D[0], T1_3D[i], T1_3D[i+1], T1_3D[0], 'CASA_TELHADO_ALA_OESTE')
        add_dxf_polyline3d(msp, T1_3D, 'CASA_BEIRAL_OESTE', closed=True)

        # Telhado 2 (Ala Leste)
        add_dxf_quad(msp, T2_3D[0], T2_3D[1], T2_3D[2], T2_3D[3], 'CASA_TELHADO_ALA_LESTE')
        add_dxf_polyline3d(msp, T2_3D, 'CASA_BEIRAL_LESTE', closed=True)

        # Piso e Paredes
        piso_pts = [(p[0], p[1], COTA_CASA) for p in CASA_WALL_UTM_2D]
        topo_pts = [(p[0], p[1], COTA_CASA + 2.80) for p in CASA_WALL_UTM_2D]
        add_dxf_polyline3d(msp, piso_pts, 'CASA_PISO', closed=True)
        for i in range(len(piso_pts)):
            nxt = (i + 1) % len(piso_pts)
            add_dxf_quad(msp, piso_pts[i], piso_pts[nxt], topo_pts[nxt], topo_pts[i], 'CASA_PAREDES')

    if kml_elements is not None:
        # KML Telhado 1
        kml_elements.append(create_kml_polygon("Telhado Ala Oeste (telhado1.kmz)", T1_3D, color_hex="cc1e40af"))
        # KML Telhado 2
        kml_elements.append(create_kml_polygon("Telhado Ala Leste (telhado2.kmz)", T2_3D, color_hex="cc1e3a8a"))
        # KML Cumeeira
        rs3 = (RS[0], RS[1], COTA_CASA + H_RIDGE)
        rn3 = (RN[0], RN[1], COTA_CASA + H_RIDGE)
        kml_elements.append(create_kml_linestring("Cumeeira Central", [rs3, rn3], color_hex="ffffffff", width=4))
        # KML Paredes
        piso_pts = [(p[0], p[1], COTA_CASA) for p in CASA_WALL_UTM_2D]
        topo_pts = [(p[0], p[1], COTA_CASA + 2.80) for p in CASA_WALL_UTM_2D]
        for i in range(len(piso_pts)):
            nxt = (i + 1) % len(piso_pts)
            kml_elements.append(create_kml_polygon(f"Parede Casa {i+1}", [piso_pts[i], piso_pts[nxt], topo_pts[nxt], topo_pts[i]], color_hex="ffeeeeee"))

def export_salao(doc=None, kml_elements=None):
    """Exporta Salão 12x8m com 36 painéis solares"""
    se, sn = SALAO_BASE_UTM
    cota = COTA_SALAO
    rot = SALAO_ROT_RAD
    
    if doc is not None:
        msp = doc.modelspace()
        # Piso
        add_dxf_box_mesh(msp, se, sn, cota, 12.0, 8.0, 0.25, rot, 'SALAO_PISO')
        
        # 6 Pilares
        p_coords = [
            (-5.7, -3.7), (0.0, -3.7), (5.7, -3.7),
            (-5.7, 3.7),  (0.0, 3.7),  (5.7, 3.7)
        ]
        for lx, lz in p_coords:
            pe, pn = local_to_utm(lx, lz, se, sn, rot)
            add_dxf_box_mesh(msp, pe, pn, cota, 0.30, 0.30, 3.60, rot, 'SALAO_PILARES')

        # Telhado Duas Águas (Cumeeira z=0 no meio)
        # Água Traseira (Norte z < 0) e Água Frontal (Sul z > 0)
        cume_pts = [
            local_to_utm(-6.4, 0.0, se, sn, rot) + (cota + 5.05,),
            local_to_utm(6.4, 0.0, se, sn, rot) + (cota + 5.05,)
        ]
        add_dxf_polyline3d(msp, cume_pts, 'SALAO_CUMEEIRA')

        beiral_sul = [
            local_to_utm(-6.4, 4.35, se, sn, rot) + (cota + 3.65,),
            local_to_utm(6.4, 4.35, se, sn, rot) + (cota + 3.65,)
        ]
        beiral_norte = [
            local_to_utm(-6.4, -4.35, se, sn, rot) + (cota + 3.65,),
            local_to_utm(6.4, -4.35, se, sn, rot) + (cota + 3.65,)
        ]
        add_dxf_quad(msp, cume_pts[0], cume_pts[1], beiral_sul[1], beiral_sul[0], 'SALAO_TELHADO_SUL')
        add_dxf_quad(msp, beiral_norte[0], beiral_norte[1], cume_pts[1], cume_pts[0], 'SALAO_TELHADO_NORTE')

        # 36 Módulos Solares (18 na água Sul, 18 na água Norte)
        # Cada água: 2 fileiras x 9 módulos (1.134m x 1.95m)
        for side, z_sign in [('SUL', 1), ('NORTE', -1)]:
            for row_idx, r_offset in enumerate([1.10, 3.10]):
                for col_idx in range(9):
                    x_col = -5.10 + col_idx * 1.16
                    z_col = z_sign * r_offset
                    # Altura calculada na inclinação
                    h_mod = 5.05 - (abs(z_col) / 4.35) * 1.40 + 0.10
                    pe, pn = local_to_utm(x_col, z_col, se, sn, rot)
                    add_dxf_box_mesh(msp, pe, pn, cota + h_mod, 1.134, 1.95, 0.04, rot, f'SALAO_SOLAR_{side}')

    if kml_elements is not None:
        # Piso
        piso_local = [(-6, -4), (6, -4), (6, 4), (-6, 4)]
        piso_3d = [local_to_utm(lx, lz, se, sn, rot) + (cota,) for lx, lz in piso_local]
        kml_elements.append(create_kml_polygon("Salão de Festas - Piso 12x8m", piso_3d, color_hex="cc64748b"))

        # Telhados
        c1 = local_to_utm(-6.4, 0.0, se, sn, rot) + (cota + 5.05,)
        c2 = local_to_utm(6.4, 0.0, se, sn, rot) + (cota + 5.05,)
        bs1 = local_to_utm(-6.4, 4.35, se, sn, rot) + (cota + 3.65,)
        bs2 = local_to_utm(6.4, 4.35, se, sn, rot) + (cota + 3.65,)
        bn1 = local_to_utm(-6.4, -4.35, se, sn, rot) + (cota + 3.65,)
        bn2 = local_to_utm(6.4, -4.35, se, sn, rot) + (cota + 3.65,)

        kml_elements.append(create_kml_polygon("Salão - Telhado Sul", [c1, c2, bs2, bs1], color_hex="ccb45309"))
        kml_elements.append(create_kml_polygon("Salão - Telhado Norte", [bn1, bn2, c2, c1], color_hex="ccb45309"))

        # Painéis Solares
        for side, z_sign in [('Sul', 1), ('Norte', -1)]:
            for row_idx, r_offset in enumerate([1.10, 3.10]):
                for col_idx in range(9):
                    x_col = -5.10 + col_idx * 1.16
                    z_col = z_sign * r_offset
                    h_mod = 5.05 - (abs(z_col) / 4.35) * 1.40 + 0.12
                    pts_m = [
                        local_to_utm(x_col - 0.55, z_col - 0.95, se, sn, rot) + (cota + h_mod,),
                        local_to_utm(x_col + 0.55, z_col - 0.95, se, sn, rot) + (cota + h_mod,),
                        local_to_utm(x_col + 0.55, z_col + 0.95, se, sn, rot) + (cota + h_mod,),
                        local_to_utm(x_col - 0.55, z_col + 0.95, se, sn, rot) + (cota + h_mod,)
                    ]
                    kml_elements.append(create_kml_polygon(f"Módulo Solar {side} F{row_idx+1}-M{col_idx+1}", pts_m, color_hex="ff0284c7"))

def export_quadra(doc=None, kml_elements=None):
    """Exporta Quadra 22x12m com telas Sul, Norte e Leste H=6m"""
    qe, qn = QUADRA_BASE_UTM
    cota = COTA_QUADRA
    rot = QUADRA_ROT_RAD
    
    if doc is not None:
        msp = doc.modelspace()
        # Caixa de areia
        add_dxf_box_mesh(msp, qe, qn, cota, 22.0, 12.0, 0.30, rot, 'QUADRA_AREIA')
        # Borda de contenção de madeira
        add_dxf_box_mesh(msp, qe, qn, cota, 22.4, 12.4, 0.40, rot, 'QUADRA_BORDA')

        # 10 Postes Metálicos (H = 6.00m)
        post_coords = [
            (-11, -6), (-5.5, -6), (0, -6), (5.5, -6), (11, -6),
            (-11, 6),  (-5.5, 6),  (0, 6),  (5.5, 6),  (11, 6)
        ]
        for lx, lz in post_coords:
            pe, pn = local_to_utm(lx, lz, qe, qn, rot)
            add_dxf_box_mesh(msp, pe, pn, cota, 0.20, 0.20, 6.00, rot, 'QUADRA_POSTES_TELAS')

        # Telas H = 6,00 m (Sul, Leste, Norte)
        # Tela Sul (z = -6.0)
        s_base_1 = local_to_utm(-11, -6, qe, qn, rot) + (cota,)
        s_base_2 = local_to_utm(11, -6, qe, qn, rot) + (cota,)
        s_top_1  = local_to_utm(-11, -6, qe, qn, rot) + (cota + 6.0,)
        s_top_2  = local_to_utm(11, -6, qe, qn, rot) + (cota + 6.0,)
        add_dxf_quad(msp, s_base_1, s_base_2, s_top_2, s_top_1, 'QUADRA_TELA_SUL')

        # Tela Norte (z = +6.0)
        n_base_1 = local_to_utm(-11, 6, qe, qn, rot) + (cota,)
        n_base_2 = local_to_utm(11, 6, qe, qn, rot) + (cota,)
        n_top_1  = local_to_utm(-11, 6, qe, qn, rot) + (cota + 6.0,)
        n_top_2  = local_to_utm(11, 6, qe, qn, rot) + (cota + 6.0,)
        add_dxf_quad(msp, n_base_1, n_base_2, n_top_2, n_top_1, 'QUADRA_TELA_NORTE')

        # Tela Leste (x = +11.0)
        e_base_1 = s_base_2
        e_base_2 = n_base_2
        e_top_1  = s_top_2
        e_top_2  = n_top_2
        add_dxf_quad(msp, e_base_1, e_base_2, e_top_2, e_top_1, 'QUADRA_TELA_LESTE')

        # Cabos de Aço Superiores
        cable_pts = [s_top_1, s_top_2, e_top_2, n_top_1]
        add_dxf_polyline3d(msp, cable_pts, 'QUADRA_CABO_SUPERIOR')

        # Rede Central de Jogo (2,20m)
        net_b1 = local_to_utm(0, -4.25, qe, qn, rot) + (cota + 1.20,)
        net_b2 = local_to_utm(0, 4.25, qe, qn, rot) + (cota + 1.20,)
        net_t1 = local_to_utm(0, -4.25, qe, qn, rot) + (cota + 2.20,)
        net_t2 = local_to_utm(0, 4.25, qe, qn, rot) + (cota + 2.20,)
        add_dxf_quad(msp, net_b1, net_b2, net_t2, net_t1, 'QUADRA_REDE_JOGO')

    if kml_elements is not None:
        # Caixa de areia
        sand_pts = [
            local_to_utm(-11, -6, qe, qn, rot) + (cota,),
            local_to_utm(11, -6, qe, qn, rot) + (cota,),
            local_to_utm(11, 6, qe, qn, rot) + (cota,),
            local_to_utm(-11, 6, qe, qn, rot) + (cota,)
        ]
        kml_elements.append(create_kml_polygon("Quadra de Areia 22x12m", sand_pts, color_hex="ccfef08a"))

        # Telas Sul, Leste, Norte
        s_b1 = local_to_utm(-11, -6, qe, qn, rot) + (cota,)
        s_b2 = local_to_utm(11, -6, qe, qn, rot) + (cota,)
        s_t1 = local_to_utm(-11, -6, qe, qn, rot) + (cota + 6.0,)
        s_t2 = local_to_utm(11, -6, qe, qn, rot) + (cota + 6.0,)
        kml_elements.append(create_kml_polygon("Tela de Proteção Sul (H=6m)", [s_b1, s_b2, s_t2, s_t1], color_hex="6638bdf8"))

        n_b1 = local_to_utm(-11, 6, qe, qn, rot) + (cota,)
        n_b2 = local_to_utm(11, 6, qe, qn, rot) + (cota,)
        n_t1 = local_to_utm(-11, 6, qe, qn, rot) + (cota + 6.0,)
        n_t2 = local_to_utm(11, 6, qe, qn, rot) + (cota + 6.0,)
        kml_elements.append(create_kml_polygon("Tela de Proteção Norte (H=6m)", [n_b1, n_b2, n_t2, n_t1], color_hex="6638bdf8"))

        kml_elements.append(create_kml_polygon("Tela de Proteção Fundo Leste (H=6m)", [s_b2, n_b2, n_t2, s_t2], color_hex="6638bdf8"))

        # Cabo de Aço
        kml_elements.append(create_kml_linestring("Cabo de Aço Perimetral Topo Telas", [s_t1, s_t2, n_t2, n_t1], color_hex="ffffffff", width=3))

def export_chales(doc=None, kml_elements=None):
    """Exporta Chalés 1 a 5 (22 m² cada) com rotação e pilotis"""
    for ch in CHALES:
        cid = ch["id"]
        ce, cn = ch["utm"]
        cota = ch["cota"]
        rot = ch["rot"]
        
        if doc is not None:
            msp = doc.modelspace()
            # 6 Pilotis descendo até o terreno natural
            piloti_coords = [
                (-2.4, -1.8), (0.0, -1.8), (2.4, -1.8),
                (-2.4, 1.8),  (0.0, 1.8),  (2.4, 1.8)
            ]
            for lx, lz in piloti_coords:
                pe, pn = local_to_utm(lx, lz, ce, cn, rot)
                add_dxf_box_mesh(msp, pe, pn, cota - 3.0, 0.25, 0.25, 3.0, rot, f'CHALE_{cid}_PILOTIS')

            # Deck / Laje de Piso (5.50m x 4.00m)
            add_dxf_box_mesh(msp, ce, cn, cota, 5.50, 4.00, 0.20, rot, f'CHALE_{cid}_DECK')

            # Corpo Principal (5.40m x 2.80m x 2.70m)
            c_pe, c_pn = local_to_utm(0.0, -0.55, ce, cn, rot)
            add_dxf_box_mesh(msp, c_pe, c_pn, cota + 0.20, 5.40, 2.80, 2.70, rot, f'CHALE_{cid}_PAREDES')

            # Telhado 2 Águas (Cumeeira no centro X=0, caindo para as laterais X)
            cume_pts = [
                local_to_utm(0.0, -2.20, ce, cn, rot) + (cota + 4.10,),
                local_to_utm(0.0, 2.20, ce, cn, rot) + (cota + 4.10,)
            ]
            add_dxf_polyline3d(msp, cume_pts, f'CHALE_{cid}_CUMEEIRA')

            beiral_esq = [
                local_to_utm(-2.90, -2.20, ce, cn, rot) + (cota + 2.75,),
                local_to_utm(-2.90, 2.20, ce, cn, rot) + (cota + 2.75,)
            ]
            beiral_dir = [
                local_to_utm(2.90, -2.20, ce, cn, rot) + (cota + 2.75,),
                local_to_utm(2.90, 2.20, ce, cn, rot) + (cota + 2.75,)
            ]
            add_dxf_quad(msp, beiral_esq[0], beiral_esq[1], cume_pts[1], cume_pts[0], f'CHALE_{cid}_TELHADO_ESQ')
            add_dxf_quad(msp, cume_pts[0], cume_pts[1], beiral_dir[1], beiral_dir[0], f'CHALE_{cid}_TELHADO_DIR')

            # Guarda-corpo da Varanda Frontal (Z = +1.95)
            gc_pe, gc_pn = local_to_utm(0.0, 1.95, ce, cn, rot)
            add_dxf_box_mesh(msp, gc_pe, gc_pn, cota + 0.20, 5.40, 0.08, 0.90, rot, f'CHALE_{cid}_VARANDA')

        if kml_elements is not None:
            # Deck
            deck_local = [(-2.75, -2.0), (2.75, -2.0), (2.75, 2.0), (-2.75, 2.0)]
            deck_3d = [local_to_utm(lx, lz, ce, cn, rot) + (cota + 0.20,) for lx, lz in deck_local]
            kml_elements.append(create_kml_polygon(f"Chalé {cid} - Deck 22 m²", deck_3d, color_hex="cc78350f"))

            # Telhado
            c1 = local_to_utm(0.0, -2.20, ce, cn, rot) + (cota + 4.10,)
            c2 = local_to_utm(0.0, 2.20, ce, cn, rot) + (cota + 4.10,)
            be1 = local_to_utm(-2.90, -2.20, ce, cn, rot) + (cota + 2.75,)
            be2 = local_to_utm(-2.90, 2.20, ce, cn, rot) + (cota + 2.75,)
            bd1 = local_to_utm(2.90, -2.20, ce, cn, rot) + (cota + 2.75,)
            bd2 = local_to_utm(2.90, 2.20, ce, cn, rot) + (cota + 2.75,)
            kml_elements.append(create_kml_polygon(f"Chalé {cid} - Telhado Ala Oeste", [be1, be2, c2, c1], color_hex="cc9a3412"))
            kml_elements.append(create_kml_polygon(f"Chalé {cid} - Telhado Ala Leste", [c1, c2, bd2, bd1], color_hex="cc9a3412"))

# ==============================================================================
# 4. SALVAMENTO DOS ARQUIVOS DXF E KMZ
# ==============================================================================

def create_dxf_document():
    doc = ezdxf.new('R2018', setup=True)
    doc.units = units.M
    return doc

def save_kmz(filename, kml_folder_dict):
    """Cria KMZ contendo pastas organizadas no KML"""
    kml_content = ["""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
  <name>Sítio das Andorinhas — Projetos Executivos 3D</name>
  <open>1</open>
"""]
    for folder_name, elems in kml_folder_dict.items():
        esc_folder = folder_name.replace("&", "&amp;")
        kml_content.append(f"""  <Folder>
    <name>{esc_folder}</name>
    <open>1</open>
""")
        kml_content.extend(elems)
        kml_content.append("  </Folder>\n")

    kml_content.append("""</Document>
</kml>""")
    full_kml = "\n".join(kml_content)
    
    kmz_path = os.path.join(SOLAR_DIR, filename)
    with zipfile.ZipFile(kmz_path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr("doc.kml", full_kml.encode('utf-8'))
    print(f"   [KMZ] Salvo: {filename} ({os.path.getsize(kmz_path):,} bytes)")

def main():
    print("================================================================================")
    print("EXPORTANDO PROJETOS 3D EM CAD (DXF) E GOOGLE EARTH (KMZ)")
    print("================================================================================")

    # 1. ARQUIVO MESTRE COMPLETO (TODAS AS EDIFICAÇÕES)
    print("\n1. Gerando Projeto Completo Unificado...")
    doc_completo = create_dxf_document()
    kml_completo = {
        "Casa do Sítio (200 m²)": [],
        "Salão de Festas (12x8m) & Usina Solar (36 Módulos)": [],
        "Quadra de Areia (22x12m) & Telas de Proteção H=6m": [],
        "Chalés 1 a 5 (22 m² cada)": []
    }
    
    export_casa(doc_completo, kml_completo["Casa do Sítio (200 m²)"])
    export_salao(doc_completo, kml_completo["Salão de Festas (12x8m) & Usina Solar (36 Módulos)"])
    export_quadra(doc_completo, kml_completo["Quadra de Areia (22x12m) & Telas de Proteção H=6m"])
    export_chales(doc_completo, kml_completo["Chalés 1 a 5 (22 m² cada)"])

    dxf_completo_path = os.path.join(SOLAR_DIR, "Projeto_Completo_Sitio_Edificacoes.dxf")
    doc_completo.saveas(dxf_completo_path)
    print(f"   [DXF] Salvo: Projeto_Completo_Sitio_Edificacoes.dxf ({os.path.getsize(dxf_completo_path):,} bytes)")
    save_kmz("Projeto_Completo_Sitio_Edificacoes.kmz", kml_completo)

    # 2. ARQUIVOS INDIVIDUAIS SEPARADOS
    print("\n2. Gerando Projetos Individuais Separados (DXF e KMZ)...")
    
    # Casa do Sítio
    doc_casa = create_dxf_document()
    kml_casa = {"Casa do Sítio": []}
    export_casa(doc_casa, kml_casa["Casa do Sítio"])
    p = os.path.join(SOLAR_DIR, "casa_do_sitio.dxf")
    doc_casa.saveas(p)
    print(f"   [DXF] Salvo: casa_do_sitio.dxf ({os.path.getsize(p):,} bytes)")
    save_kmz("casa_do_sitio.kmz", kml_casa)

    # Salão de Festas
    doc_salao = create_dxf_document()
    kml_salao = {"Salão de Festas 12x8m": []}
    export_salao(doc_salao, kml_salao["Salão de Festas 12x8m"])
    p = os.path.join(SOLAR_DIR, "salao_de_festas_12x8m.dxf")
    doc_salao.saveas(p)
    print(f"   [DXF] Salvo: salao_de_festas_12x8m.dxf ({os.path.getsize(p):,} bytes)")
    save_kmz("salao_de_festas_12x8m.kmz", kml_salao)

    # Quadra de Areia
    doc_quadra = create_dxf_document()
    kml_quadra = {"Quadra de Areia 22x12m": []}
    export_quadra(doc_quadra, kml_quadra["Quadra de Areia 22x12m"])
    p = os.path.join(SOLAR_DIR, "quadra_de_areia_22x12m.dxf")
    doc_quadra.saveas(p)
    print(f"   [DXF] Salvo: quadra_de_areia_22x12m.dxf ({os.path.getsize(p):,} bytes)")
    save_kmz("quadra_de_areia_22x12m.kmz", kml_quadra)

    # Chalés 1 a 5
    doc_chales = create_dxf_document()
    kml_chales = {"Chalés 1 a 5": []}
    export_chales(doc_chales, kml_chales["Chalés 1 a 5"])
    p = os.path.join(SOLAR_DIR, "chales_1_a_5.dxf")
    doc_chales.saveas(p)
    print(f"   [DXF] Salvo: chales_1_a_5.dxf ({os.path.getsize(p):,} bytes)")
    save_kmz("chales_1_a_5.kmz", kml_chales)

    print("\nTodos os arquivos DXF e KMZ foram exportados com sucesso absoluto!")

if __name__ == "__main__":
    main()
