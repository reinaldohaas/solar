#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
EXPORTADOR CAD EXECUTIVO PROFISSIONAL (DXF R2000 / AUTOCAD)
PROJETO: SÍTIO ANDORINHAS - CASAS, QUADRA DE AREIA, SALÃO E CHALÉS
===============================================================================
Gera projetos executivos individuais em formato CAD Autodesk DXF R2000 (compatível
com 100% das versões de AutoCAD, DWG TrueView, Civil 3D, Revit, SketchUp e QGIS).

CORREÇÃO CRÍTICA DE ENQUADRAMENTO E ESCALA:
  - Os desenhos de plantas executivas ficam estritamente em coordenadas locais (origem 0,0),
    garantindo que ao abrir no AutoCAD/TrueView, o ZOOM EXTENTS preencha a tela perfeitamente,
    sem áreas vazias de 660 km causadas pela mistura de (0,0) com coordenadas UTM.
  - Os modelos georreferenciados ficam em arquivos dedicados '_3D_UTM.dxf' e na Implantação
    Geral, estritamente no fuso UTM 22S (SIRGAS 2000), sem nenhum objeto na origem (0,0).
"""

import os
import math
import numpy as np
import geopandas as gpd
import ezdxf
from ezdxf import units

OUT_DIR = r"C:\Users\haas\github\solar\export_cad"
os.makedirs(OUT_DIR, exist_ok=True)
GPKG_NATIVO = r"C:\Users\haas\github\solar\Projeto_Solar_SIGSC_Nativo.gpkg"


def setup_standard_layers(doc):
    """Configura layers técnicos padrão ABNT/AutoCAD com cores e espessuras de pena."""
    layers_def = [
        ('ARQ_PAREDES', 7, 0.50),         # Branco/Preto contorno grosso
        ('ARQ_PAREDES_BAIXAS', 8, 0.25),  # Cinza
        ('ARQ_PISO_LAJE', 8, 0.25),       # Cinza escuro
        ('ARQ_COBERTURA', 1, 0.35),       # Vermelho / Telhado
        ('ARQ_ESQUADRIAS', 4, 0.20),      # Ciano / Portas e janelas
        ('ARQ_PILAR', 6, 0.50),           # Magenta / Pilares
        ('ESTRUTURA_POSTES', 7, 0.50),    # Branco
        ('ESTRUTURA_REDES', 8, 0.20),     # Cinza escuro
        ('ESTRUTURA_CABOS', 6, 0.30),     # Magenta
        ('AREIA_BORDA', 40, 0.40),        # Laranja / Terra
        ('AREIA_PISO', 251, 0.15),        # Areia suave
        ('QUADRA_JOGO', 5, 0.35),         # Azul royal
        ('EQUIPAMENTOS', 4, 0.30),        # Ciano
        ('SOLAR_PAINEIS', 150, 0.35),     # Azul solar
        ('COTAS', 3, 0.18),               # Verde
        ('TEXTOS', 2, 0.20),              # Amarelo
        ('TITULOS', 7, 0.45),             # Branco / Destaque
        ('HACHURAS', 251, 0.10),          # Cinza claríssimo
        ('PRANCHA_SELO', 7, 0.60),        # Bordas
        ('LIMITE_PROPRIEDADE', 1, 0.60),  # Vermelho forte
        ('GEORREF_3D', 2, 0.30)           # Amarelo / 3D no espaço real
    ]
    for name, color, lw in layers_def:
        if name not in doc.layers:
            l = doc.layers.add(name, color=color)
            l.lineweight = int(lw * 100)


def add_selo_abnt(msp, x0, y0, largura, altura, titulo_desenho, escala="1:1 (Métrico)", prancha="01/01"):
    """Desenha prancha e selo técnico ABNT no ModelSpace perfeitamente ajustado ao desenho."""
    msp.add_lwpolyline([(x0, y0), (x0 + largura, y0), (x0 + largura, y0 + altura), (x0, y0 + altura)],
                       dxfattribs={'layer': 'PRANCHA_SELO', 'closed': True})
    m = 1.0
    msp.add_lwpolyline([(x0 + m, y0 + m), (x0 + largura - m, y0 + m),
                        (x0 + largura - m, y0 + altura - m), (x0 + m, y0 + altura - m)],
                       dxfattribs={'layer': 'PRANCHA_SELO', 'closed': True})
    
    sw, sh = 18.0, 6.0
    sx = x0 + largura - m - sw
    sy = y0 + m
    msp.add_lwpolyline([(sx, sy), (sx + sw, sy), (sx + sw, sy + sh), (sx, sy + sh)],
                       dxfattribs={'layer': 'PRANCHA_SELO', 'closed': True})
    msp.add_line((sx, sy + 4.0), (sx + sw, sy + 4.0), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((sx, sy + 2.0), (sx + sw, sy + 2.0), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((sx + 9.0, sy), (sx + 9.0, sy + 2.0), dxfattribs={'layer': 'PRANCHA_SELO'})

    msp.add_text("PROJETO EXECUTIVO CAD - SÍTIO ANDORINHAS", dxfattribs={'layer': 'TITULOS', 'height': 0.35}).set_placement((sx + 0.5, sy + 4.8))
    msp.add_text(f"CONTEÚDO: {titulo_desenho.upper()}", dxfattribs={'layer': 'TEXTOS', 'height': 0.30}).set_placement((sx + 0.5, sy + 2.8))
    msp.add_text(f"ESCALA: {escala} (1 un = 1,00 m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((sx + 0.5, sy + 0.8))
    msp.add_text(f"PRANCHA: {prancha} | SIRGAS 2000 UTM 22S", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((sx + 9.3, sy + 0.8))


# =============================================================================
# 1. CASA DO SÍTIO (Casa Principal)
# =============================================================================
def exportar_casa_do_sitio():
    print("\n--- 1. Gerando Casa_do_Sitio.dxf ---")
    doc = ezdxf.new('R2000')
    doc.units = units.M
    msp = doc.modelspace()
    setup_standard_layers(doc)

    wallUTM = [
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
    ]
    cx = np.mean([p[0] for p in wallUTM])
    cy = np.mean([p[1] for p in wallUTM])
    h_cumeeira = 4.60
    h_beiral = 3.10

    # 1.1 PLANTA BAIXA ARQUITETÔNICA LOCAL (Origem 0,0)
    ox, oy = 0.0, 0.0
    msp.add_text("1. PLANTA BAIXA ARQUITETÔNICA - CASA DO SÍTIO", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((ox - 8.0, oy + 12.0))
    msp.add_text("Escala 1:1 | Dimensões em metros | Cota Piso Acabado = +540,90m", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox - 8.0, oy + 11.2))

    wall_local = [(p[0] - cx, p[1] - cy) for p in wallUTM]
    msp.add_lwpolyline(wall_local, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    Rs_local = (663412.325 - cx, 6968630.680 - cy)
    Rn_local = (663415.670 - cx, 6968642.765 - cy)
    msp.add_line(Rs_local, Rn_local, dxfattribs={'layer': 'ARQ_COBERTURA'})
    msp.add_text("CUMEEIRA CENTRAL (h = +4,60m)", dxfattribs={'layer': 'ARQ_COBERTURA', 'height': 0.20}).set_placement(((Rs_local[0]+Rn_local[0])/2 - 2.5, (Rs_local[1]+Rn_local[1])/2))

    # Ambientes
    msp.add_text("VARANDA / DECK", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox - 4.0, oy - 2.5))
    msp.add_text("SALA DE ESTAR / LAREIRA", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox - 2.0, oy + 1.0))
    msp.add_text("COZINHA INTEGRADA", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox + 2.5, oy + 1.5))
    msp.add_text("SUÍTE MASTER", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox + 3.0, oy - 2.5))
    msp.add_text("DORMITÓRIO HÓSPEDES", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox - 1.5, oy + 5.0))
    msp.add_text("B.W.C.", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((ox + 2.0, oy + 5.0))

    msp.add_line((ox - 3.0, oy - 3.5), (ox - 1.8, oy - 3.5), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_line((ox + 1.5, oy - 4.5), (ox + 3.5, oy - 4.5), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})

    # 1.2 CORTE TRANSVERSAL ESQUEMÁTICO (x = 22, y = 0)
    cx0, cy0 = 22.0, 0.0
    msp.add_text("2. CORTE TRANSVERSAL ESQUEMÁTICO (DUAS ÁGUAS)", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((cx0, cy0 + 12.0))
    msp.add_line((cx0 - 8.0, cy0), (cx0 + 8.0, cy0), dxfattribs={'layer': 'ARQ_PISO_LAJE'})
    msp.add_text("NÍVEL DO PISO = +540,90m", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((cx0 - 7.5, cy0 - 0.4))
    msp.add_line((cx0 - 4.5, cy0), (cx0 - 4.5, cy0 + h_beiral), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((cx0 + 4.5, cy0), (cx0 + 4.5, cy0 + h_beiral), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((cx0 - 5.5, cy0 + h_beiral - 0.2), (cx0, cy0 + h_cumeeira), dxfattribs={'layer': 'ARQ_COBERTURA'})
    msp.add_line((cx0 + 5.5, cy0 + h_beiral - 0.2), (cx0, cy0 + h_cumeeira), dxfattribs={'layer': 'ARQ_COBERTURA'})
    msp.add_text(f"CUMEEIRA: +{h_cumeeira:.2f}m", dxfattribs={'layer': 'ARQ_COBERTURA', 'height': 0.22}).set_placement((cx0 - 1.5, cy0 + h_cumeeira + 0.3))
    msp.add_text(f"BEIRAL: +{h_beiral:.2f}m", dxfattribs={'layer': 'ARQ_COBERTURA', 'height': 0.20}).set_placement((cx0 - 6.5, cy0 + h_beiral))

    # Moldura e selo ABNT (Bounding box perfeito: -12 a 38 em X, -8 a 16 em Y)
    add_selo_abnt(msp, -12.0, -8.0, 50.0, 24.0, "CASA DO SÍTIO - PLANTA BAIXA E CORTE")

    dxf_file = os.path.join(OUT_DIR, "Casa_do_Sitio.dxf")
    doc.saveas(dxf_file)
    print(f"  [OK] DXF gerado: {os.path.basename(dxf_file)}")

    # Gera também a versão 3D Georreferenciada pura
    doc3d = ezdxf.new('R2000')
    doc3d.units = units.M
    msp3d = doc3d.modelspace()
    setup_standard_layers(doc3d)
    cota_piso = 540.90
    for i in range(len(wallUTM)):
        p1 = wallUTM[i]
        p2 = wallUTM[(i + 1) % len(wallUTM)]
        v_wall = [
            (p1[0], p1[1], cota_piso),
            (p2[0], p2[1], cota_piso),
            (p2[0], p2[1], cota_piso + h_beiral),
            (p1[0], p1[1], cota_piso + h_beiral)
        ]
        msp3d.add_3dface(v_wall, dxfattribs={'layer': 'GEORREF_3D'})
    Rs_utm = (663412.325, 6968630.680, cota_piso + h_cumeeira)
    Rn_utm = (663415.670, 6968642.765, cota_piso + h_cumeeira)
    msp3d.add_line(Rs_utm, Rn_utm, dxfattribs={'layer': 'GEORREF_3D'})
    dxf_3d = os.path.join(OUT_DIR, "Casa_do_Sitio_3D_UTM.dxf")
    doc3d.saveas(dxf_3d)
    print(f"  [OK] DXF 3D UTM gerado: {os.path.basename(dxf_3d)}")
    return dxf_file, dxf_3d


# =============================================================================
# 2. QUADRA DE AREIA 22x12m
# =============================================================================
def exportar_quadra_de_areia():
    print("\n--- 2. Gerando Quadra_de_Areia_22x12m.dxf ---")
    doc = ezdxf.new('R2000')
    doc.units = units.M
    msp = doc.modelspace()
    setup_standard_layers(doc)

    L = 22.00
    W = 12.00
    H_net = 6.00

    # 2.1 PLANTA BAIXA DA ARENA
    ox, oy = 0.0, 0.0
    msp.add_text("1. PLANTA BAIXA - ARENA MULTIESPORTE EM AREIA", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((ox, oy + W + 2.8))
    msp.add_text("Escala 1:1 | Dimensões em metros | Caixa de Areia 22,00 m × 12,00 m (264 m²)", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox, oy + W + 2.0))

    msp.add_lwpolyline([(ox, oy), (ox + L, oy), (ox + L, oy + W), (ox, oy + W)], dxfattribs={'layer': 'AREIA_BORDA', 'closed': True})
    msp.add_lwpolyline([(ox + 0.15, oy + 0.15), (ox + L - 0.15, oy + 0.15), (ox + L - 0.15, oy + W - 0.15), (ox + 0.15, oy + W - 0.15)], dxfattribs={'layer': 'AREIA_BORDA', 'closed': True})

    qx, qy = ox + 3.00, oy + 2.00
    qL, qW = 16.00, 8.00
    msp.add_lwpolyline([(qx, qy), (qx + qL, qy), (qx + qL, qy + qW), (qx, qy + qW)], dxfattribs={'layer': 'QUADRA_JOGO', 'closed': True})
    msp.add_text("LINHAS OFICIAIS DE JOGO (16,00 m × 8,00 m)", dxfattribs={'layer': 'QUADRA_JOGO', 'height': 0.22}).set_placement((qx + 4.5, qy + 1.2))
    msp.add_text("Vôlei de Praia / Futevôlei / Beach Tennis", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((qx + 4.6, qy + 0.7))

    x_mid = ox + L / 2.0
    msp.add_line((x_mid, oy + 0.5), (x_mid, oy + W - 0.5), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_circle((x_mid, qy - 0.8), radius=0.10, dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_circle((x_mid, qy + qW + 0.8), radius=0.10, dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_text("MASTRO E REDE CENTRAL (h=2,43m)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.20}).set_placement((x_mid - 3.2, oy + W / 2.0 + 0.4))

    for sign, gx in [(-1, ox + 0.8), (1, ox + L - 0.8)]:
        msp.add_lwpolyline([(gx, oy + 4.50), (gx, oy + 7.50), (gx + sign * 0.8, oy + 7.50), (gx + sign * 0.8, oy + 4.50)], dxfattribs={'layer': 'EQUIPAMENTOS', 'closed': True})
        msp.add_text("GOL (3x2m)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.18}).set_placement((gx - 0.8, oy + 5.7))

    postes = [
        (ox, oy), (ox + 5.5, oy), (ox + 11.0, oy), (ox + 16.5, oy), (ox + L, oy),
        (ox, oy + W), (ox + 5.5, oy + W), (ox + 11.0, oy + W), (ox + 16.5, oy + W), (ox + L, oy + W)
    ]
    for px, py in postes:
        msp.add_circle((px, py), radius=0.15, dxfattribs={'layer': 'ESTRUTURA_POSTES'})
        msp.add_text("P(6m)", dxfattribs={'layer': 'ESTRUTURA_POSTES', 'height': 0.15}).set_placement((px + 0.2, py + 0.2))

    # 2.2 CORTE LONGITUDINAL C-C (22,00m)
    cx, cy = 0.0, -10.0
    msp.add_text("2. CORTE LONGITUDINAL C-C (22,00 m) COM REDE DE COBERTURA", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((cx, cy + 8.5))
    msp.add_line((cx, cy), (cx + L, cy), dxfattribs={'layer': 'AREIA_BORDA'})
    msp.add_line((cx, cy - 0.35), (cx + L, cy - 0.35), dxfattribs={'layer': 'AREIA_BORDA'})
    msp.add_text("COLCHÃO DE AREIA LAVADA (e = 35 cm) | COTA +547,25m", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((cx + 5.0, cy - 0.2))
    
    for px in [0.0, 5.5, 11.0, 16.5, 22.0]:
        msp.add_line((cx + px, cy), (cx + px, cy + H_net), dxfattribs={'layer': 'ESTRUTURA_POSTES'})
        msp.add_circle((cx + px, cy + H_net), radius=0.12, dxfattribs={'layer': 'ESTRUTURA_POSTES'})
    msp.add_line((cx, cy + H_net), (cx + L, cy + H_net), dxfattribs={'layer': 'ESTRUTURA_REDES'})
    msp.add_text("REDE DE PROTEÇÃO SUPERIOR (h = +6,00 m)", dxfattribs={'layer': 'ESTRUTURA_REDES', 'height': 0.22}).set_placement((cx + 4.0, cy + H_net + 0.4))

    add_selo_abnt(msp, -3.0, -14.0, 32.0, 31.0, "ARENA DE AREIA MULTIESPORTE 22x12m")

    dxf_file = os.path.join(OUT_DIR, "Quadra_de_Areia_22x12m.dxf")
    doc.saveas(dxf_file)
    print(f"  [OK] DXF gerado: {os.path.basename(dxf_file)}")

    # Versão 3D Georreferenciada pura
    doc3d = ezdxf.new('R2000')
    doc3d.units = units.M
    msp3d = doc3d.modelspace()
    setup_standard_layers(doc3d)
    cota_areia = 547.25
    ang = math.radians(31.02)
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    quadra_cx, quadra_cy = 663435.5, 6968660.0

    def to_utm(lx, ly):
        dx = lx - L / 2.0
        dy = ly - W / 2.0
        gx = quadra_cx + (dx * cos_a - dy * sin_a)
        gy = quadra_cy + (dx * sin_a + dy * cos_a)
        return gx, gy

    p_borda_utm = [to_utm(p[0], p[1]) for p in [(0, 0), (L, 0), (L, W), (0, W)]]
    msp3d.add_polyline3d([(p[0], p[1], cota_areia) for p in p_borda_utm] + [(p_borda_utm[0][0], p_borda_utm[0][1], cota_areia)], dxfattribs={'layer': 'GEORREF_3D'})
    for px, py in postes:
        gx, gy = to_utm(px, py)
        msp3d.add_line((gx, gy, cota_areia), (gx, gy, cota_areia + H_net), dxfattribs={'layer': 'GEORREF_3D'})
    dxf_3d = os.path.join(OUT_DIR, "Quadra_de_Areia_3D_UTM.dxf")
    doc3d.saveas(dxf_3d)
    print(f"  [OK] DXF 3D UTM gerado: {os.path.basename(dxf_3d)}")
    return dxf_file, dxf_3d


# =============================================================================
# 3. SALÃO 12x8m COM USINA SOLAR 10,44 kWp
# =============================================================================
def exportar_salao():
    print("\n--- 3. Gerando Salao_12x8m.dxf ---")
    doc = ezdxf.new('R2000')
    doc.units = units.M
    msp = doc.modelspace()
    setup_standard_layers(doc)

    L = 11.00
    W = 8.11
    t = 0.20

    # 3.1 PLANTA BAIXA ARQUITETÔNICA
    ox, oy = 0.0, 0.0
    msp.add_text("1. PLANTA BAIXA ARQUITETÔNICA - SALÃO MULTIUSO", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((ox, oy + W + 2.5))
    msp.add_text("Escala 1:1 | Dimensões em metros | Área Total = 89,21 m² | Cota Piso = +547,05m", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox, oy + W + 1.8))

    msp.add_lwpolyline([(ox, oy), (ox + L, oy), (ox + L, oy + W), (ox, oy + W)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
    msp.add_lwpolyline([(ox + t, oy + t), (ox + L - t, oy + t), (ox + L - t, oy + W - t), (ox + t, oy + W - t)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    x_apoio = ox + L - 2.80
    msp.add_line((x_apoio, oy + t), (x_apoio, oy + W - t), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((x_apoio + t, oy + t), (x_apoio + t, oy + W - t), dxfattribs={'layer': 'ARQ_PAREDES'})
    y_div_wc = oy + W / 2.0
    msp.add_line((x_apoio + t, y_div_wc), (ox + L - t, y_div_wc), dxfattribs={'layer': 'ARQ_PAREDES'})

    msp.add_text("SALÃO DE EVENTOS / CONVIVÊNCIA", dxfattribs={'layer': 'TEXTOS', 'height': 0.28}).set_placement((ox + 2.0, oy + 4.0))
    msp.add_text("SANITÁRIO MASCULINO", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((x_apoio + 0.3, y_div_wc + 1.5))
    msp.add_text("SANITÁRIO FEMININO", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((x_apoio + 0.3, oy + 1.5))

    msp.add_line((ox + 3.5, oy), (ox + 5.5, oy), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_arc((ox + 3.5, oy), radius=1.0, start_angle=0, end_angle=90, dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_arc((ox + 5.5, oy), radius=1.0, start_angle=90, end_angle=180, dxfattribs={'layer': 'ARQ_ESQUADRIAS'})

    # 3.2 PLANTA DE COBERTURA COM ARRANJO SOLAR FOTOVOLTAICO
    cx, cy = 15.0, 0.0
    msp.add_text("2. PLANTA DE COBERTURA & USINA SOLAR (10,44 kWp)", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((cx, cy + W + 2.5))
    msp.add_text("18 Módulos Fotovoltaicos 580W TOPCon (2,278 m × 1,134 m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((cx, cy + W + 1.8))
    msp.add_lwpolyline([(cx, cy), (cx + L, cy), (cx + L, cy + W), (cx, cy + W)], dxfattribs={'layer': 'ARQ_COBERTURA', 'closed': True})

    mx0 = cx + 0.80
    my0 = cy + 2.00
    for r in range(2):
        for c in range(9):
            px = mx0 + c * 1.05
            py = my0 + r * 2.45
            msp.add_lwpolyline([(px, py), (px + 1.00, py), (px + 1.00, py + 2.25), (px, py + 2.25)], dxfattribs={'layer': 'SOLAR_PAINEIS', 'closed': True})

    add_selo_abnt(msp, -2.0, -6.0, 32.0, 20.0, "SALÃO 12x8m COM USINA FOTOVOLTAICA")

    dxf_file = os.path.join(OUT_DIR, "Salao_12x8m.dxf")
    doc.saveas(dxf_file)
    print(f"  [OK] DXF gerado: {os.path.basename(dxf_file)}")

    # Versão 3D Georreferenciada pura
    doc3d = ezdxf.new('R2000')
    doc3d.units = units.M
    msp3d = doc3d.modelspace()
    setup_standard_layers(doc3d)
    cota_salao = 547.05
    h_plati = 3.90
    ang = math.radians(31.02)
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    salao_cx, salao_cy = 663428.0, 6968652.0

    def to_utm(lx, ly):
        dx = lx - L / 2.0
        dy = ly - W / 2.0
        gx = salao_cx + (dx * cos_a - dy * sin_a)
        gy = salao_cy + (dx * sin_a + dy * cos_a)
        return gx, gy

    p_salao_utm = [to_utm(p[0], p[1]) for p in [(0, 0), (L, 0), (L, W), (0, W)]]
    for i in range(4):
        p1 = p_salao_utm[i]
        p2 = p_salao_utm[(i + 1) % 4]
        v_wall = [
            (p1[0], p1[1], cota_salao),
            (p2[0], p2[1], cota_salao),
            (p2[0], p2[1], cota_salao + h_plati),
            (p1[0], p1[1], cota_salao + h_plati)
        ]
        msp3d.add_3dface(v_wall, dxfattribs={'layer': 'GEORREF_3D'})
    dxf_3d = os.path.join(OUT_DIR, "Salao_12x8m_3D_UTM.dxf")
    doc3d.saveas(dxf_3d)
    print(f"  [OK] DXF 3D UTM gerado: {os.path.basename(dxf_3d)}")
    return dxf_file, dxf_3d


# =============================================================================
# 4. CHALÉS 1 A 5
# =============================================================================
def exportar_chales():
    print("\n--- 4. Gerando Chales_1_a_5.dxf ---")
    doc = ezdxf.new('R2000')
    doc.units = units.M
    msp = doc.modelspace()
    setup_standard_layers(doc)

    chales_utm = [
        {"id": 1, "utm": (663457.29, 6968674.96), "cota": 544.50},
        {"id": 2, "utm": (663448.54, 6968667.08), "cota": 545.20},
        {"id": 3, "utm": (663438.93, 6968659.26), "cota": 545.90},
        {"id": 4, "utm": (663466.65, 6968618.00), "cota": 542.80},
        {"id": 5, "utm": (663469.69, 6968600.54), "cota": 541.60}
    ]

    cL = 7.00
    cW = 5.00

    # 4.1 PLANTA ARQUITETÔNICA PADRÃO DO CHALÉ (7x5m)
    ox, oy = 0.0, 0.0
    msp.add_text("1. PLANTA ARQUITETÔNICA PADRÃO DO CHALÉ (7,00 m × 5,00 m)", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((ox, oy + cW + 2.5))
    msp.add_text("Área Construída = 35,00 m² | 1 Suíte Master com Varanda Panorâmica e BWC", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox, oy + cW + 1.8))

    msp.add_lwpolyline([(ox, oy), (ox + cL, oy), (ox + cL, oy + cW), (ox, oy + cW)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    # Varanda
    msp.add_line((ox + 2.00, oy), (ox + 2.00, oy + cW), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_text("VARANDA PANORÂMICA", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((ox + 0.3, oy + 2.5))

    # Banheiro
    msp.add_line((ox + cL - 1.80, oy + cW - 2.20), (ox + cL, oy + cW - 2.20), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((ox + cL - 1.80, oy + cW), (ox + cL - 1.80, oy + cW - 2.20), dxfattribs={'layer': 'ARQ_PAREDES'})

    msp.add_text("SUÍTE / DORMITÓRIO CASAL", dxfattribs={'layer': 'TEXTOS', 'height': 0.25}).set_placement((ox + 2.5, oy + 2.0))
    msp.add_text("B.W.C.", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((ox + cL - 1.5, oy + cW - 1.2))

    # Portas
    msp.add_line((ox + 2.0, oy + 1.0), (ox + 2.0, oy + 1.9), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_arc((ox + 2.0, oy + 1.0), radius=0.9, start_angle=0, end_angle=90, dxfattribs={'layer': 'ARQ_ESQUADRIAS'})

    # 4.2 PLANTA DE IMPLANTAÇÃO DOS 5 CHALÉS NO TERRENO (Relativa)
    ix, iy = 14.0, 0.0
    msp.add_text("2. PLANTA DE IMPLANTAÇÃO DOS CHALÉS 1 A 5", dxfattribs={'layer': 'TITULOS', 'height': 0.45}).set_placement((ix, iy + 16.0))
    c1_utm = chales_utm[0]["utm"]
    for c in chales_utm:
        rel_x = ix + (c["utm"][0] - c1_utm[0]) * 0.30
        rel_y = iy + (c["utm"][1] - c1_utm[1]) * 0.30
        msp.add_lwpolyline([(rel_x, rel_y), (rel_x + 3.0, rel_y), (rel_x + 3.0, rel_y + 2.2), (rel_x, rel_y + 2.2)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
        msp.add_text(f"CHALÉ {c['id']}", dxfattribs={'layer': 'TITULOS', 'height': 0.26}).set_placement((rel_x + 0.3, rel_y + 1.0))
        msp.add_text(f"Cota +{c['cota']:.1f}m", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((rel_x + 0.3, rel_y + 0.4))

    add_selo_abnt(msp, -2.0, -6.0, 36.0, 25.0, "CHALÉS 1 A 5 - ARQUITETURA E IMPLANTAÇÃO")

    dxf_file = os.path.join(OUT_DIR, "Chales_1_a_5.dxf")
    doc.saveas(dxf_file)
    print(f"  [OK] DXF gerado: {os.path.basename(dxf_file)}")

    # Versão 3D Georreferenciada pura
    doc3d = ezdxf.new('R2000')
    doc3d.units = units.M
    msp3d = doc3d.modelspace()
    setup_standard_layers(doc3d)
    for c in chales_utm:
        gx, gy = c["utm"]
        gz = c["cota"]
        p_chale_3d = [
            (gx - cL/2, gy - cW/2, gz),
            (gx + cL/2, gy - cW/2, gz),
            (gx + cL/2, gy + cW/2, gz),
            (gx - cL/2, gy + cW/2, gz)
        ]
        msp3d.add_polyline3d(p_chale_3d + [p_chale_3d[0]], dxfattribs={'layer': 'GEORREF_3D'})
        for k in range(4):
            p1 = p_chale_3d[k]
            p2 = p_chale_3d[(k + 1) % 4]
            v_wall = [
                (p1[0], p1[1], gz),
                (p2[0], p2[1], gz),
                (p2[0], p2[1], gz + 2.80),
                (p1[0], p1[1], gz + 2.80)
            ]
            msp3d.add_3dface(v_wall, dxfattribs={'layer': 'GEORREF_3D'})
        msp3d.add_line((gx - cL/2, gy, gz + 3.80), (gx + cL/2, gy, gz + 3.80), dxfattribs={'layer': 'GEORREF_3D'})
    dxf_3d = os.path.join(OUT_DIR, "Chales_1_a_5_3D_UTM.dxf")
    doc3d.saveas(dxf_3d)
    print(f"  [OK] DXF 3D UTM gerado: {os.path.basename(dxf_3d)}")
    return dxf_file, dxf_3d


# =============================================================================
# 5. COMPLEXO GERAL (MASTER PLAN GEORREFERENCIADO NO SIRGAS 2000)
# =============================================================================
def exportar_complexo_geral():
    print("\n--- 5. Gerando Complexo_Geral_Casas_e_Quadra.dxf ---")
    doc = ezdxf.new('R2000')
    doc.units = units.M
    msp = doc.modelspace()
    setup_standard_layers(doc)

    # 5.1 LIMITE DA PROPRIEDADE (Do GPKG nativo do SIGSC)
    if os.path.exists(GPKG_NATIVO):
        try:
            gdf_limite = gpd.read_file(GPKG_NATIVO, layer='limite_sitio')
            geom = gdf_limite.geometry.iloc[0]
            if geom.geom_type == 'Polygon':
                coords = list(geom.exterior.coords)
                msp.add_lwpolyline(coords, dxfattribs={'layer': 'LIMITE_PROPRIEDADE', 'closed': True})
                msp.add_text("LIMITE PERIMETRAL DO SÍTIO ANDORINHAS", dxfattribs={'layer': 'LIMITE_PROPRIEDADE', 'height': 2.0}).set_placement((coords[0][0] + 5.0, coords[0][1] + 5.0))
        except Exception as e:
            print(f"  [AVISO] Nao foi possivel carregar limite do gpkg: {e}")

    # 5.2 CASA DO SÍTIO
    wallUTM = [
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
    ]
    msp.add_lwpolyline(wallUTM, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
    msp.add_text("CASA DO SÍTIO (PISO +540,90m)", dxfattribs={'layer': 'TITULOS', 'height': 0.60}).set_placement((663414.0, 6968636.0))
    msp.add_line((663412.325, 6968630.680), (663415.670, 6968642.765), dxfattribs={'layer': 'ARQ_COBERTURA'})

    # 5.3 QUADRA DE AREIA 22x12m
    qL, qW = 22.00, 12.00
    ang = math.radians(31.02)
    cos_a, sin_a = math.cos(ang), math.sin(ang)
    quadra_cx, quadra_cy = 663435.5, 6968660.0

    def to_q_utm(lx, ly):
        dx = lx - qL / 2.0
        dy = ly - qW / 2.0
        gx = quadra_cx + (dx * cos_a - dy * sin_a)
        gy = quadra_cy + (dx * sin_a + dy * cos_a)
        return gx, gy

    p_quadra = [to_q_utm(p[0], p[1]) for p in [(0, 0), (qL, 0), (qL, qW), (0, qW)]]
    msp.add_lwpolyline(p_quadra, dxfattribs={'layer': 'AREIA_BORDA', 'closed': True})
    msp.add_text("QUADRA DE AREIA 22x12m (+547,25m)", dxfattribs={'layer': 'TITULOS', 'height': 0.60}).set_placement((quadra_cx - 6.0, quadra_cy))

    # 5.4 SALÃO 12x8m
    sL, sW = 11.00, 8.11
    salao_cx, salao_cy = 663428.0, 6968652.0

    def to_s_utm(lx, ly):
        dx = lx - sL / 2.0
        dy = ly - sW / 2.0
        gx = salao_cx + (dx * cos_a - dy * sin_a)
        gy = salao_cy + (dx * sin_a + dy * cos_a)
        return gx, gy

    p_salao = [to_s_utm(p[0], p[1]) for p in [(0, 0), (sL, 0), (sL, sW), (0, sW)]]
    msp.add_lwpolyline(p_salao, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
    msp.add_text("SALÃO 12x8m & SOLAR 10,44 kWp (+547,05m)", dxfattribs={'layer': 'TITULOS', 'height': 0.60}).set_placement((salao_cx - 6.0, salao_cy))

    # 5.5 CHALÉS 1 A 5
    chales_utm = [
        {"id": 1, "utm": (663457.29, 6968674.96), "cota": 544.50},
        {"id": 2, "utm": (663448.54, 6968667.08), "cota": 545.20},
        {"id": 3, "utm": (663438.93, 6968659.26), "cota": 545.90},
        {"id": 4, "utm": (663466.65, 6968618.00), "cota": 542.80},
        {"id": 5, "utm": (663469.69, 6968600.54), "cota": 541.60}
    ]
    cL, cW = 7.00, 5.00
    for c in chales_utm:
        gx, gy = c["utm"]
        p_chale = [
            (gx - cL/2, gy - cW/2),
            (gx + cL/2, gy - cW/2),
            (gx + cL/2, gy + cW/2),
            (gx - cL/2, gy + cW/2)
        ]
        msp.add_lwpolyline(p_chale, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
        msp.add_text(f"CHALÉ {c['id']} (+{c['cota']:.1f}m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.40}).set_placement((gx - 3.0, gy))

    # Selo no espaço UTM próximo às edificações (sem nenhum objeto em 0,0)
    add_selo_abnt(msp, 663380.0, 6968560.0, 120.0, 140.0, "IMPLANTAÇÃO GERAL GEORREFERENCIADA - SÍTIO ANDORINHAS", escala="1:1 UTM 22S")

    dxf_file = os.path.join(OUT_DIR, "Complexo_Geral_Casas_e_Quadra.dxf")
    doc.saveas(dxf_file)
    print(f"  [OK] DXF gerado: {os.path.basename(dxf_file)}")
    return dxf_file


def main():
    print("=" * 80)
    print("INICIANDO EXPORTAÇÃO CAD EXECUTIVA EM ESCALA MÉTRICA 1:1 RIGOROSA")
    print("=" * 80)
    # Remove eventuais DWGs corrompidos gerados pelo libredwg
    for f in os.listdir(OUT_DIR):
        if f.endswith(".dwg"):
            try:
                os.remove(os.path.join(OUT_DIR, f))
                print(f"  [LIMPEZA] Removido arquivo DWG binario nao-conforme: {f}")
            except Exception:
                pass

    f1 = exportar_casa_do_sitio()
    f2 = exportar_quadra_de_areia()
    f3 = exportar_salao()
    f4 = exportar_chales()
    f5 = exportar_complexo_geral()
    print("=" * 80)
    print("EXPORTAÇÃO FINALIZADA COM SUCESSO!")
    print(f"1. Casa do Sítio:                  {f1[0]}")
    print(f"2. Quadra de Areia 22x12m:         {f2[0]}")
    print(f"3. Salão 12x8m:                    {f3[0]}")
    print(f"4. Chalés 1 a 5:                   {f4[0]}")
    print(f"5. Complexo Geral Georreferenciado: {f5}")
    print("=" * 80)


if __name__ == '__main__':
    main()
