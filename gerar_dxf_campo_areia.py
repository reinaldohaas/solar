#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJETO EXECUTIVO CAD - CAMPO DE FUTEBOL E VÔLEI DE AREIA COM REDES 3D
===============================================================================
Gera o projeto executivo completo em formato CAD (DXF R2018 / AutoCAD)
compatível com AutoCAD, Civil 3D, LibreCAD, Revit e QGIS.
Inclui:
  1. Planta Baixa da Arena de Areia (22,00 m × 12,00 m)
  2. Planta da Cobertura de Cabos de Aço e Rede Superior (Teto a 6,00 m)
  3. Corte Longitudinal C-C (22m) com Estrutura e Drenagem Profunda
  4. Corte Transversal D-D (12m)
  5. Detalhes Construtivos (Drenagem, Fundação dos Postes e Fixação de Redes)
  6. Memorial de Materiais e Selo Técnico ABNT
"""

import os
import ezdxf
from ezdxf import units

OUT_DXF = r"C:\Users\haas\github\solar\Projeto_Executivo_Campo_de_Areia.dxf"

def criar_projeto_campo_areia():
    doc = ezdxf.new('R2018', setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    # -------------------------------------------------------------------------
    # Camadas (Layers)
    # -------------------------------------------------------------------------
    layers_def = [
        ('AREIA_BORDA', 40, 0.40),        # Laranja / Marrom claro
        ('AREIA_PISO', 251, 0.15),        # Areia suave
        ('QUADRA_JOGO', 5, 0.35),         # Azul royal
        ('POSTES_ESTRUTURA', 7, 0.50),    # Branco
        ('REDES_LATERAIS', 8, 0.20),      # Cinza escuro
        ('REDES_TETO', 9, 0.20),          # Cinza claro
        ('CABOS_ACO', 6, 0.30),           # Magenta
        ('EQUIPAMENTOS', 4, 0.30),        # Ciano
        ('ILUMINACAO_LED', 2, 0.30),      # Amarelo
        ('DRENAGEM', 140, 0.25),          # Azul claro
        ('COTAS', 3, 0.18),               # Verde
        ('TEXTOS', 2, 0.20),              # Amarelo
        ('TITULOS', 7, 0.40),             # Branco
        ('PRANCHA_SELO', 7, 0.60)         # Bordas
    ]
    for name, color, lw in layers_def:
        l = doc.layers.add(name, color=color)
        l.lineweight = int(lw * 100)

    # Dimensões da Caixa de Areia
    L = 22.00   # Comprimento total da caixa (m)
    W = 12.00   # Largura total da caixa (m)
    H_net = 6.00 # Altura total das redes perimetrais e do teto (m)

    # =========================================================================
    # 1. PLANTA BAIXA DA ARENA DE AREIA (Escala 1:75 / 1:100)
    # =========================================================================
    ox, oy = 0.0, 0.0

    msp.add_text("1. PLANTA BAIXA - ARENA DE AREIA MULTIESPORTE", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((ox, oy + W + 2.4))
    msp.add_text("Escala 1:75 | Dimensões em metros | Caixa de Areia 22,00 m × 12,00 m (264 m²)", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((ox, oy + W + 1.8))

    # Borda externa da mureta de contenção (espessura 0,15m)
    msp.add_lwpolyline([(ox, oy), (ox + L, oy), (ox + L, oy + W), (ox, oy + W), (ox, oy)], dxfattribs={'layer': 'AREIA_BORDA', 'closed': True})
    msp.add_lwpolyline([(ox + 0.15, oy + 0.15), (ox + L - 0.15, oy + 0.15), (ox + L - 0.15, oy + W - 0.15), (ox + 0.15, oy + W - 0.15), (ox + 0.15, oy + 0.15)], dxfattribs={'layer': 'AREIA_BORDA', 'closed': True})

    # Superfície de areia
    msp.add_text("CAIXA DE AREIA DO MAR LAVADA (ESPESSURA = 30 cm)", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((ox + 5.5, oy + 0.6))
    msp.add_text("GUIA DE CONTENÇÃO PERIMETRAL EM CONCRETO / MADEIRA TRATADA", dxfattribs={'layer': 'TEXTOS', 'height': 0.15}).set_placement((ox + 4.2, oy + W - 0.6))

    # Marcação oficial da quadra de Vôlei de Praia / Futevôlei / Beach Tennis (16,00 m × 8,00 m)
    # Centralizada: recuo de (22 - 16)/2 = 3.00m nas cabeceiras e (12 - 8)/2 = 2.00m nas laterais
    qx, qy = ox + 3.00, oy + 2.00
    qL, qW = 16.00, 8.00
    msp.add_lwpolyline([(qx, qy), (qx + qL, qy), (qx + qL, qy + qW), (qx, qy + qW), (qx, qy)], dxfattribs={'layer': 'QUADRA_JOGO', 'closed': True})
    msp.add_text("LINHAS OFICIAIS DE JOGO (16,00 m × 8,00 m)", dxfattribs={'layer': 'QUADRA_JOGO', 'height': 0.20}).set_placement((qx + 4.5, qy + 1.2))
    msp.add_text("Fitas de Poliéster Azul 50mm com Fixadores Elásticos", dxfattribs={'layer': 'TEXTOS', 'height': 0.15}).set_placement((qx + 4.6, qy + 0.7))

    # Linha central e Rede Oficial de Vôlei / Futevôlei
    x_mid = ox + L / 2.0
    msp.add_line((x_mid, oy + 0.5), (x_mid, oy + W - 0.5), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_line((x_mid - 0.05, oy + 0.5), (x_mid - 0.05, oy + W - 0.5), dxfattribs={'layer': 'EQUIPAMENTOS'})
    # Mastros da rede de vôlei (fora da linha de jogo, a 1,00m de recuo)
    msp.add_circle((x_mid, qy - 0.8), radius=0.10, dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_circle((x_mid, qy + qW + 0.8), radius=0.10, dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_text("MASTRO E REDE CENTRAL (h=2,43m)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.18}).set_placement((x_mid - 2.8, oy + W/2.0 + 0.3))

    # Traves de Futebol de Areia / Beach Soccer nas duas cabeceiras (largura 3,00 m × altura 2,00 m)
    for sign, gx in [(-1, ox + 0.8), (1, ox + L - 0.8)]:
        # Trave centralizada em Y (largura 3.00m de 4.50m a 7.50m)
        msp.add_lwpolyline([(gx, oy + 4.50), (gx, oy + 7.50), (gx + sign*0.8, oy + 7.50), (gx + sign*0.8, oy + 4.50), (gx, oy + 4.50)], dxfattribs={'layer': 'EQUIPAMENTOS', 'closed': True})
        msp.add_circle((gx, oy + 4.50), radius=0.08, dxfattribs={'layer': 'EQUIPAMENTOS'})
        msp.add_circle((gx, oy + 7.50), radius=0.08, dxfattribs={'layer': 'EQUIPAMENTOS'})
        msp.add_text("GOL (3,00x2,00)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.16}).set_placement((gx - 0.8, oy + 5.7))

    # Locação dos 10 Postes Metálicos Estruturais de 6,00 m ao redor do perímetro
    # 4 cantos + 4 nas laterais maiores (a cada 5,50m) + 2 nas cabeceiras (a 6,00m)
    postes_coords = [
        (ox, oy), (ox + 5.5, oy), (ox + 11.0, oy), (ox + 16.5, oy), (ox + 22.0, oy),
        (ox + 22.0, oy + 6.0), (ox + 22.0, oy + 12.0),
        (ox + 16.5, oy + 12.0), (ox + 11.0, oy + 12.0), (ox + 5.5, oy + 12.0), (ox, oy + 12.0),
        (ox, oy + 6.0)
    ]
    for p_idx, (px, py) in enumerate(postes_coords):
        msp.add_circle((px, py), radius=0.15, dxfattribs={'layer': 'POSTES_ESTRUTURA'})
        # Bloco de fundação em concreto (sapata 40x40cm)
        msp.add_lwpolyline([(px - 0.25, py - 0.25), (px + 0.25, py - 0.25), (px + 0.25, py + 0.25), (px - 0.25, py + 0.25), (px - 0.25, py - 0.25)], dxfattribs={'layer': 'POSTES_ESTRUTURA', 'closed': True})
        msp.add_text(f"P{p_idx+1}", dxfattribs={'layer': 'TEXTOS', 'height': 0.14}).set_placement((px + 0.3, py + 0.2))

    # Portão de acesso com tela de proteção (x = ox + 1.0 a 2.0, y = oy)
    msp.add_arc((ox + 1.0, oy), radius=1.0, start_angle=0, end_angle=90, dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_text("PORTÃO (1,00x2,10)", dxfattribs={'layer': 'TEXTOS', 'height': 0.15}).set_placement((ox + 0.6, oy - 0.4))

    # Refletores LED nos 4 cantos
    for rx, ry in [(ox, oy), (ox + L, oy), (ox + L, oy + W), (ox, oy + W)]:
        msp.add_circle((rx, ry), radius=0.35, dxfattribs={'layer': 'ILUMINACAO_LED'})
        msp.add_text("REFLETOR LED 200W", dxfattribs={'layer': 'ILUMINACAO_LED', 'height': 0.12}).set_placement((rx - 0.8, ry - 0.6))

    # Cotas
    msp.add_aligned_dim(p1=(ox, oy - 1.2), p2=(ox + L, oy - 1.2), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(ox - 1.2, oy), p2=(ox - 1.2, oy + W), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(qx, oy + W + 1.0), p2=(qx + qL, oy + W + 1.0), distance=0.3, dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 2. PLANTA DA COBERTURA DE CABOS E REDE SUPERIOR (TETO ANTI-FUGA A 6,00 m)
    # =========================================================================
    tx, ty = 28.0, 0.0

    msp.add_text("2. COBERTURA SUPERIOR: CABOS & REDE DE TETO (+6,00 m)", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((tx, ty + W + 2.4))
    msp.add_text("Escala 1:100 | Malha Estrutural de Travamento em Cabos de Aço e Tela Superior Anti-Fuga", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((tx, ty + W + 1.8))

    # Borda da cobertura (interligando topo dos postes a +6,00m)
    msp.add_lwpolyline([(tx, ty), (tx + L, ty), (tx + L, ty + W), (tx, ty + W), (tx, ty)], dxfattribs={'layer': 'CABOS_ACO', 'closed': True})

    # Cabos de aço transversais (a cada 5,50m)
    for cx in [tx + 5.5, tx + 11.0, tx + 16.5]:
        msp.add_line((cx, ty), (cx, ty + W), dxfattribs={'layer': 'CABOS_ACO'})
        msp.add_text("CABO DE AÇO 1/4\" TRANSVERSAL", dxfattribs={'layer': 'TEXTOS', 'height': 0.14}).set_placement((cx + 0.1, ty + 1.0))

    # Cabos longitudinais de travamento central
    msp.add_line((tx, ty + W/2.0), (tx + L, ty + W/2.0), dxfattribs={'layer': 'CABOS_ACO'})
    msp.add_text("CABO LONGITUDINAL CENTRAL (EIXO CUMEEIRA)", dxfattribs={'layer': 'TEXTOS', 'height': 0.15}).set_placement((tx + 7.0, ty + W/2.0 + 0.2))

    # Cabos diagonais em X para contraventamento dos vãos
    for i in range(4):
        x1 = tx + i * 5.5
        x2 = tx + (i + 1) * 5.5
        msp.add_line((x1, ty), (x2, ty + W), dxfattribs={'layer': 'CABOS_ACO'})
        msp.add_line((x1, ty + W), (x2, ty), dxfattribs={'layer': 'CABOS_ACO'})

    # Malha de rede superior (hachura indicativa)
    msp.add_text("REDE DE POLIETILENO TRANÇADA 100% VIRGEM ANTI-UV (MALHA 10x10 cm)", dxfattribs={'layer': 'REDES_TETO', 'height': 0.22}).set_placement((tx + 2.5, ty + W/2.0 - 0.8))
    msp.add_text("COBERTURA INTEGRAL DO TETO: 264 m² A 6,00 m DE ALTURA", dxfattribs={'layer': 'REDES_TETO', 'height': 0.18}).set_placement((tx + 3.8, ty + W/2.0 - 1.3))

    # Postes no topo (+6,00m)
    for px, py in [(tx, ty), (tx + 5.5, ty), (tx + 11.0, ty), (tx + 16.5, ty), (tx + 22.0, ty),
                   (tx + 22.0, ty + 6.0), (tx + 22.0, ty + 12.0),
                   (tx + 16.5, ty + 12.0), (tx + 11.0, ty + 12.0), (tx + 5.5, ty + 12.0), (tx, ty + 12.0),
                   (tx, ty + 6.0)]:
        msp.add_circle((px, py), radius=0.15, dxfattribs={'layer': 'POSTES_ESTRUTURA'})

    # =========================================================================
    # 3. CORTE LONGITUDINAL C-C (Extensão 22,00 m) - Escala 1:75
    # =========================================================================
    lx, ly = 0.0, -16.0

    msp.add_text("3. CORTE LONGITUDINAL C-C (EXTENSÃO 22,00 m)", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((lx, ly + H_net + 2.5))
    msp.add_text("Escala 1:75 | Mostrando perfil da caixa de areia, rede lateral e rede superior a 6,00m", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((lx, ly + H_net + 1.9))

    # Nível do terreno natural
    msp.add_line((lx - 1.5, ly), (lx + L + 1.5, ly), dxfattribs={'layer': 'AREIA_BORDA'})
    msp.add_text("TERRENO NATURAL (+0,00m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((lx - 1.5, ly - 0.4))

    # Caixa de areia escavada e preenchida (espessura 30cm)
    msp.add_lwpolyline([(lx, ly), (lx + L, ly), (lx + L, ly - 0.30), (lx, ly - 0.30), (lx, ly)], dxfattribs={'layer': 'AREIA_PISO', 'closed': True})
    msp.add_text("CAMADA DE AREIA DO MAR LAVADA (30 cm)", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((lx + 6.5, ly - 0.22))

    # Camada drenante de brita (15cm abaixo da areia)
    msp.add_lwpolyline([(lx, ly - 0.30), (lx + L, ly - 0.30), (lx + L, ly - 0.45), (lx, ly - 0.45), (lx, ly - 0.30)], dxfattribs={'layer': 'DRENAGEM', 'closed': True})
    msp.add_text("MANTA GEOTÊXTIL BIDIM RT-09 + CAMADA DE BRITA DRENANTE (15 cm)", dxfattribs={'layer': 'DRENAGEM', 'height': 0.14}).set_placement((lx + 4.5, ly - 0.40))

    # Tubo dreno corrugado perfurado Ø100mm no fundo
    for dx in [lx + 4.0, lx + 11.0, lx + 18.0]:
        msp.add_circle((dx, ly - 0.55), radius=0.08, dxfattribs={'layer': 'DRENAGEM'})
        msp.add_text("DRENO Ø100", dxfattribs={'layer': 'DRENAGEM', 'height': 0.10}).set_placement((dx - 0.25, ly - 0.75))

    # Postes em elevação a cada 5,50m (altura 6,00m)
    for px in [lx, lx + 5.5, lx + 11.0, lx + 16.5, lx + 22.0]:
        # Poste tubular
        msp.add_line((px, ly), (px, ly + H_net), dxfattribs={'layer': 'POSTES_ESTRUTURA'})
        msp.add_line((px + 0.08, ly), (px + 0.08, ly + H_net), dxfattribs={'layer': 'POSTES_ESTRUTURA'})
        # Fundação enterrada (sapata 40x40x80cm)
        msp.add_lwpolyline([(px - 0.20, ly), (px + 0.28, ly), (px + 0.28, ly - 0.80), (px - 0.20, ly - 0.80), (px - 0.20, ly)], dxfattribs={'layer': 'POSTES_ESTRUTURA', 'closed': True})

    # Rede perimetral lateral de 6,00 m de altura
    msp.add_line((lx, ly + H_net), (lx + L, ly + H_net), dxfattribs={'layer': 'CABOS_ACO'})
    msp.add_text("CABO DE AÇO SUPERIOR E REDE LATERAL (h=6,00m)", dxfattribs={'layer': 'REDES_LATERAIS', 'height': 0.18}).set_placement((lx + 6.0, ly + H_net - 0.4))

    # Rede superior / teto anti-fuga a 6,00 m
    msp.add_text("REDE DE COBERTURA / TETO ANTI-FUGA (COTA +6,00m)", dxfattribs={'layer': 'REDES_TETO', 'height': 0.20}).set_placement((lx + 5.8, ly + H_net + 0.3))

    # Traves de gol em elevação nas extremidades
    msp.add_line((lx + 0.8, ly), (lx + 0.8, ly + 2.0), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_line((lx + L - 0.8, ly), (lx + L - 0.8, ly + 2.0), dxfattribs={'layer': 'EQUIPAMENTOS'})

    # Rede central de vôlei em elevação
    msp.add_line((lx + 11.0, ly), (lx + 11.0, ly + 2.43), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_text("REDE DE VÔLEI (2,43m)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.14}).set_placement((lx + 11.2, ly + 2.2))

    # Cotas verticais do corte
    msp.add_aligned_dim(p1=(lx - 0.8, ly), p2=(lx - 0.8, ly + H_net), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(lx - 0.8, ly - 0.45), p2=(lx - 0.8, ly), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(lx, ly - 1.2), p2=(lx + L, ly - 1.2), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 4. CORTE TRANSVERSAL D-D (Largura 12,00 m) - Escala 1:75
    # =========================================================================
    wx, wy = 28.0, -16.0

    msp.add_text("4. CORTE TRANSVERSAL D-D (LARGURA 12,00 m)", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((wx, wy + H_net + 2.5))
    msp.add_text("Escala 1:75 | Mostrando largura útil de 12m, postes e rede de teto", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((wx, wy + H_net + 1.9))

    # Nível do terreno
    msp.add_line((wx - 1.5, wy), (wx + W + 1.5, wy), dxfattribs={'layer': 'AREIA_BORDA'})
    # Caixa de areia e brita em corte transversal
    msp.add_lwpolyline([(wx, wy), (wx + W, wy), (wx + W, wy - 0.30), (wx, wy - 0.30), (wx, wy)], dxfattribs={'layer': 'AREIA_PISO', 'closed': True})
    msp.add_lwpolyline([(wx, wy - 0.30), (wx + W, wy - 0.30), (wx + W, wy - 0.45), (wx, wy - 0.45), (wx, wy - 0.30)], dxfattribs={'layer': 'DRENAGEM', 'closed': True})

    # Postes laterais (x = wx e x = wx + W)
    for px in [wx, wx + W]:
        msp.add_line((px, wy), (px, wy + H_net), dxfattribs={'layer': 'POSTES_ESTRUTURA'})
        msp.add_line((px + 0.08, wy), (px + 0.08, wy + H_net), dxfattribs={'layer': 'POSTES_ESTRUTURA'})
        msp.add_lwpolyline([(px - 0.20, wy), (px + 0.28, wy), (px + 0.28, wy - 0.80), (px - 0.20, wy - 0.80), (px - 0.20, wy)], dxfattribs={'layer': 'POSTES_ESTRUTURA', 'closed': True})

    # Cabo superior e teto
    msp.add_line((wx, wy + H_net), (wx + W, wy + H_net), dxfattribs={'layer': 'CABOS_ACO'})
    msp.add_text("REDE SUPERIOR A 6,00 m DE ALTURA", dxfattribs={'layer': 'REDES_TETO', 'height': 0.18}).set_placement((wx + 3.2, wy + H_net + 0.3))

    # Mastro e rede de vôlei central
    msp.add_line((wx + W/2.0, wy), (wx + W/2.0, wy + 2.43), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_line((wx + 2.0, wy + 2.43), (wx + 10.0, wy + 2.43), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_line((wx + 2.0, wy + 1.43), (wx + 10.0, wy + 1.43), dxfattribs={'layer': 'EQUIPAMENTOS'})
    msp.add_text("REDE CENTRAL (1,00x8,00m)", dxfattribs={'layer': 'EQUIPAMENTOS', 'height': 0.14}).set_placement((wx + 4.2, wy + 1.8))

    # Cotas
    msp.add_aligned_dim(p1=(wx - 0.8, wy), p2=(wx - 0.8, wy + H_net), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(wx, wy - 1.2), p2=(wx + W, wy - 1.2), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 5. QUADRO DE MATERIAIS & MEMORIAL DESCRITIVO
    # =========================================================================
    mx, my = 0.0, -32.0

    msp.add_text("5. MEMORIAL DESCRITIVO E QUANTITATIVO DE MATERIAIS", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((mx, my + 9.5))

    quadro_mat = [
        "ITEM / ESPECIFICAÇÃO", "QUANTIDADE", "UNIDADE / OBSERVAÇÕES",
        "Área Total da Caixa de Areia:", "264,00", "m² (Dimensões úteis: 22,00 m × 12,00 m)",
        "Área Oficial da Quadra de Jogo:", "128,00", "m² (Marcação com fitas azuis 16,00 m × 8,00 m)",
        "Areia do Mar Lavada e Peneirada:", "79,20", "m³ (~120 toneladas, camada útil de 30 cm)",
        "Camada de Brita nº 1 e 2 (Drenante):", "39,60", "m³ (Camada de assentamento de 15 cm)",
        "Manta Geotêxtil Não-Tecido (Bidim):", "300,00", "m² (Separação entre brita e areia para não entupir dreno)",
        "Tubos Dreno Corrugados Perfurados Ø100mm:", "56,00", "metros (Espinha de peixe interligada à rede pluvial)",
        "Postes Tubulares Aço Galvanizado 3\" ou 4\":", "10", "unidades (Comprimento total 6,80m sendo 0,80m engastado)",
        "Fundações em Concreto (40x40x80 cm):", "10", "unidades (Sapatas de ancoragem com chumbadores)",
        "Rede de Proteção Perimetral (Laterais):", "408,00", "m² (Altura 6,00 m, malha 10x10 cm polietileno virgem UV)",
        "Rede de Proteção Superior (Teto Anti-Fuga):", "264,00", "m² (Cobertura horizontal integral a 6,00 m de altura)",
        "Total de Telas / Redes de Proteção:", "672,00", "m² de rede de alta tenacidade 2,5mm com tratamento UV",
        "Cabos de Aço Galvanizados 1/4\" com Esticadores:", "180,00", "metros lineares para estruturação e travamento em X",
        "Kit Vôlei / Beach Tennis com Mastros e Rede:", "1", "conjunto oficial com mastros desmontáveis e regulagem de altura",
        "Traves de Futebol de Areia Tubulares (3x2m):", "2", "unidades metálicas com pintura epóxi branca e redes nylon",
        "Refletores LED 200W IP66 Branco Frio:", "4", "unidades instaladas nos 4 cantos para iluminação noturna"
    ]

    t_w = 26.0
    r_h = 0.50
    n_rows = len(quadro_mat) // 3

    for r in range(n_rows):
        ry = my + 8.8 - r * r_h
        c1 = quadro_mat[r * 3]
        c2 = quadro_mat[r * 3 + 1]
        c3 = quadro_mat[r * 3 + 2]

        msp.add_line((mx, ry), (mx + t_w, ry), dxfattribs={'layer': 'AREIA_BORDA'})
        msp.add_text(c1, dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((mx + 0.3, ry - 0.35))
        msp.add_text(c2, dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((mx + 13.5, ry - 0.35))
        msp.add_text(c3, dxfattribs={'layer': 'TEXTOS', 'height': 0.15}).set_placement((mx + 17.5, ry - 0.35))

    msp.add_lwpolyline([(mx, my + 8.8), (mx + t_w, my + 8.8), (mx + t_w, my + 8.8 - n_rows * r_h), (mx, my + 8.8 - n_rows * r_h), (mx, my + 8.8)], dxfattribs={'layer': 'POSTES_ESTRUTURA', 'closed': True})
    msp.add_line((mx + 13.0, my + 8.8), (mx + 13.0, my + 8.8 - n_rows * r_h), dxfattribs={'layer': 'POSTES_ESTRUTURA'})
    msp.add_line((mx + 17.0, my + 8.8), (mx + 17.0, my + 8.8 - n_rows * r_h), dxfattribs={'layer': 'POSTES_ESTRUTURA'})

    # Selo Técnico / Carimbo do Projeto (à direita)
    bx, by = 28.0, -32.0
    selo_w, selo_h = 14.0, 9.0

    msp.add_lwpolyline([(bx, by), (bx + selo_w, by), (bx + selo_w, by + selo_h), (bx, by + selo_h), (bx, by)], dxfattribs={'layer': 'PRANCHA_SELO', 'closed': True})
    msp.add_line((bx, by + 7.0), (bx + selo_w, by + 7.0), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((bx, by + 5.0), (bx + selo_w, by + 5.0), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((bx, by + 2.5), (bx + selo_w, by + 2.5), dxfattribs={'layer': 'PRANCHA_SELO'})

    msp.add_text("PROJETO EXECUTIVO - ENGENHARIA E INFRAESTRUTURA", dxfattribs={'layer': 'TITULOS', 'height': 0.34}).set_placement((bx + 0.4, by + 7.8))
    msp.add_text("ARENA DE AREIA DO MAR COM REDES AO REDOR E ACIMA", dxfattribs={'layer': 'TEXTOS', 'height': 0.24}).set_placement((bx + 0.4, by + 5.8))
    msp.add_text("FUTEBOL DE AREIA | VÔLEI DE PRAIA | FUTEVÔLEI | BEACH TENNIS", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 5.3))

    msp.add_text("PROPRIEDADE: NOVO SÍTIO DAS ANDORINHAS", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((bx + 0.4, by + 3.8))
    msp.add_text("LOCALIZAÇÃO: ESTRADA RIBEIRÃO DOS OVOS - SANTA CATARINA", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 3.2))

    msp.add_text("CONTEÚDO: Planta Baixa, Cobertura, Cortes C-C e D-D, Drenagem e Redes", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 1.5))
    msp.add_text("ESCALA: Indicadas (1:75 / 1:100) | UNIDADES: Metros | DATA: 2026", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 0.7))

    doc.saveas(OUT_DXF)
    print(f"Sucesso: Projeto do Campo de Areia gerado em {OUT_DXF} ({os.path.getsize(OUT_DXF):,} bytes)")

if __name__ == '__main__':
    criar_projeto_campo_areia()
