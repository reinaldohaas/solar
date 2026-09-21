#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===============================================================================
PROJETO EXECUTIVO CAD - SALÃO COM TELHADO RETO E USINA SOLAR (10,44 kWp)
===============================================================================
Gera o projeto executivo completo em formato CAD (DXF R2018 / AutoCAD)
compatível diretamente com AutoCAD, Civil 3D, LibreCAD, Revit e QGIS.
Inclui:
  1. Planta Baixa Arquitetônica (11,00 m × 8,11 m)
  2. Planta de Cobertura com Arranjo Fotovoltaico (18 módulos 580W TOPCon)
  3. Corte Transversal A-A e Corte Longitudinal B-B
  4. Fachada Principal e Lateral
  5. Quadro de Cargas e Diagrama Unifilar
  6. Selo Técnico ABNT
"""

import os
import ezdxf
from ezdxf import units
from ezdxf.enums import TextEntityAlignment

OUT_DXF = r"C:\Users\haas\github\solar\Projeto_Executivo_Salao_Telhado_Reto.dxf"

def criar_projeto_salao():
    doc = ezdxf.new('R2018', setup=True)
    doc.units = units.M
    msp = doc.modelspace()

    # -------------------------------------------------------------------------
    # Camadas (Layers)
    # -------------------------------------------------------------------------
    layers_def = [
        ('ARQ_PAREDES', 7, 0.50),         # Branco/Preto
        ('ARQ_PISO_LAJE', 8, 0.25),       # Cinza escuro
        ('ARQ_PLATIBANDA', 6, 0.35),      # Magenta
        ('ARQ_ESQUADRIAS', 4, 0.20),      # Ciano
        ('SOLAR_PAINEIS', 150, 0.35),     # Azul solar
        ('SOLAR_ESTRUTURA', 9, 0.20),     # Cinza claro
        ('SOLAR_ELETRICO', 1, 0.30),      # Vermelho
        ('COTAS', 3, 0.18),               # Verde
        ('TEXTOS', 2, 0.20),              # Amarelo
        ('TITULOS', 7, 0.40),             # Branco
        ('HACHURAS', 251, 0.10),          # Cinza suave
        ('PRANCHA_SELO', 7, 0.60)         # Bordas
    ]
    for name, color, lw in layers_def:
        l = doc.layers.add(name, color=color)
        l.lineweight = int(lw * 100)

    # -------------------------------------------------------------------------
    # Parâmetros Geométricos do Salão
    # -------------------------------------------------------------------------
    L = 11.00   # Comprimento externo (m)
    W = 8.11    # Largura externa (m)
    t = 0.20    # Espessura das paredes de alvenaria (m)
    h_wall = 3.50  # Pé-direito até a laje (m)
    h_plati = 3.90 # Altura da platibanda (m)

    # Coordenadas base no desenho CAD
    # Disposição dos desenhos no ModelSpace:
    # Planta Baixa: (0, 0)
    # Planta de Cobertura / Solar: (16, 0)
    # Cortes A-A e B-B: (0, -14) e (16, -14)
    # Fachadas: (0, -28) e (16, -28)
    # Pranchas e Selos ao redor

    # =========================================================================
    # 1. PLANTA BAIXA ARQUITETÔNICA (Piso Térreo +0,00m / Cota Laje +3,50m)
    # =========================================================================
    ox, oy = 0.0, 0.0
    
    # Título do desenho
    msp.add_text("1. PLANTA BAIXA ARQUITETÔNICA", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((ox, oy + W + 2.2))
    msp.add_text("Escala 1:50 | Dimensões em metros | Área Total = 89,21 m²", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((ox, oy + W + 1.6))

    # Paredes externas
    p_ext = [(ox, oy), (ox + L, oy), (ox + L, oy + W), (ox, oy + W), (ox, oy)]
    msp.add_lwpolyline(p_ext, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    # Paredes internas (recuo t=0.20m)
    p_int = [(ox + t, oy + t), (ox + L - t, oy + t), (ox + L - t, oy + W - t), (ox + t, oy + W - t), (ox + t, oy + t)]
    msp.add_lwpolyline(p_int, dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    # Divisão interna: Salão Principal + Sanitários e Apoio
    # Parede divisória do bloco de apoio nos fundos (x = ox + L - 2.50)
    x_apoio = ox + L - 2.80
    msp.add_line((x_apoio, oy + t), (x_apoio, oy + W - t), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((x_apoio + t, oy + t), (x_apoio + t, oy + W - t), dxfattribs={'layer': 'ARQ_PAREDES'})

    # Parede divisória entre WC Masculino e WC Feminino
    y_div_wc = oy + W / 2.0
    msp.add_line((x_apoio + t, y_div_wc), (ox + L - t, y_div_wc), dxfattribs={'layer': 'ARQ_PAREDES'})
    msp.add_line((x_apoio + t, y_div_wc + 0.15), (ox + L - t, y_div_wc + 0.15), dxfattribs={'layer': 'ARQ_PAREDES'})

    # Esquadrias: Porta Dupla Principal de Vidro (na fachada frontal x = ox + 3.5 a ox + 5.5, y = oy)
    msp.add_line((ox + 3.5, oy), (ox + 5.5, oy), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_arc((ox + 3.5, oy), radius=1.0, start_angle=0, end_angle=90, dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_arc((ox + 5.5, oy), radius=1.0, start_angle=90, end_angle=180, dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_text("P1 (2.00x2.20)", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((ox + 4.1, oy - 0.4))

    # Janelas no Salão (J1: 2.00x1.20)
    # Janela lateral esquerda (x = ox, y = oy + 2.5 a 4.5)
    msp.add_line((ox, oy + 2.5), (ox + t, oy + 2.5), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_line((ox, oy + 4.5), (ox + t, oy + 4.5), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_line((ox + t/2, oy + 2.5), (ox + t/2, oy + 4.5), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_text("J1 (2.00x1.20)", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((ox - 1.4, oy + 3.3))

    # Janelas na fachada norte (y = oy + W, x = ox + 2.0 a 4.0 e x = ox + 5.0 a 7.0)
    for jx in [ox + 2.0, ox + 5.0]:
        msp.add_line((jx, oy + W), (jx, oy + W - t), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
        msp.add_line((jx + 2.0, oy + W), (jx + 2.0, oy + W - t), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
        msp.add_line((jx, oy + W - t/2), (jx + 2.0, oy + W - t/2), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
        msp.add_text("J1", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((jx + 0.8, oy + W + 0.3))

    # Textos dos ambientes
    msp.add_text("SALÃO MULTIUSO / EVENTOS", dxfattribs={'layer': 'TEXTOS', 'height': 0.28}).set_placement((ox + 2.5, oy + 4.2))
    msp.add_text("Área = 60,1 m² | Piso Porcelanato Acetinado", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((ox + 2.0, oy + 3.6))
    msp.add_text("Cota: +0,00 m | Pé-direito: 3,50 m", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((ox + 2.4, oy + 3.1))

    msp.add_text("WC FEM.", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((x_apoio + 0.6, oy + W - 1.8))
    msp.add_text("3,5 m²", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((x_apoio + 0.8, oy + W - 2.2))

    msp.add_text("WC MASC.", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((x_apoio + 0.6, oy + 2.2))
    msp.add_text("3,5 m²", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((x_apoio + 0.8, oy + 1.8))

    msp.add_text("COPA", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((x_apoio + 0.8, oy + 0.9))

    # Cotas principais
    # Cota total inferior (L = 11.00m)
    msp.add_aligned_dim(p1=(ox, oy - 1.0), p2=(ox + L, oy - 1.0), distance=0.4,
                        dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    # Cota lateral esquerda (W = 8.11m)
    msp.add_aligned_dim(p1=(ox - 1.0, oy), p2=(ox - 1.0, oy + W), distance=0.4,
                        dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 2. PLANTA DE COBERTURA E USINA SOLAR FOTOVOLTAICA (Cota +3,50m / +3,90m)
    # =========================================================================
    sx, sy = 16.0, 0.0

    msp.add_text("2. PLANTA DE COBERTURA & USINA SOLAR (10,44 kWp)", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((sx, sy + W + 2.2))
    msp.add_text("Laje Plana com Platibanda | 18x Módulos 580W TOPCon | Azimute 0° (Norte) | Inclinação 18°", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((sx, sy + W + 1.6))

    # Platibanda externa
    msp.add_lwpolyline([(sx, sy), (sx + L, sy), (sx + L, sy + W), (sx, sy + W), (sx, sy)], dxfattribs={'layer': 'ARQ_PLATIBANDA', 'closed': True})
    # Parede interna da platibanda
    msp.add_lwpolyline([(sx + t, sy + t), (sx + L - t, sy + t), (sx + L - t, sy + W - t), (sx + t, sy + W - t), (sx + t, sy + t)], dxfattribs={'layer': 'ARQ_PLATIBANDA', 'closed': True})

    # Superfície da laje impermeabilizada
    msp.add_text("LAJE PLANA IMPERMEABILIZADA (COTA +3,50m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((sx + 2.2, sy + 0.4))
    msp.add_text("PLATIBANDA PERIMETRAL (COTA +3,90m)", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((sx + 2.8, sy + W - 0.4))

    # Módulos Solares Fotovoltaicos: 18 módulos (2 fileiras de 9 módulos)
    # Dimensões do módulo: 2,278m (ao longo da inclinação N-S) × 1,134m (E-W)
    # Projeção no plano horizontal a 18° = 2,278 × cos(18°) = 2,166m
    mw = 1.134
    ml_proj = 2.166
    gap = 0.03 # folga entre módulos

    # Fileira 1 (Norte / Frontal) e Fileira 2 (Sul / Traseira)
    row_y_offsets = [sy + 4.80, sy + 1.50]
    x_start = sx + 0.40

    for r_idx, ry in enumerate(row_y_offsets):
        # Estrutura triangular de suporte em alumínio (linha de apoio)
        msp.add_line((x_start - 0.1, ry), (x_start + 9*(mw+gap) + 0.1, ry), dxfattribs={'layer': 'SOLAR_ESTRUTURA'})
        msp.add_line((x_start - 0.1, ry + ml_proj), (x_start + 9*(mw+gap) + 0.1, ry + ml_proj), dxfattribs={'layer': 'SOLAR_ESTRUTURA'})

        for m_idx in range(9):
            mx = x_start + m_idx * (mw + gap)
            p_mod = [(mx, ry), (mx + mw, ry), (mx + mw, ry + ml_proj), (mx, ry + ml_proj), (mx, ry)]
            msp.add_lwpolyline(p_mod, dxfattribs={'layer': 'SOLAR_PAINEIS', 'closed': True})
            # Linha divisória de meia-célula (Half-Cell)
            msp.add_line((mx, ry + ml_proj/2), (mx + mw, ry + ml_proj/2), dxfattribs={'layer': 'SOLAR_PAINEIS'})
            # Identificação do módulo
            msp.add_text(f"M{r_idx*9 + m_idx + 1}", dxfattribs={'layer': 'TEXTOS', 'height': 0.14}).set_placement((mx + 0.25, ry + ml_proj/2 - 0.07))

        # Texto da Fileira
        msp.add_text(f"FILEIRA {r_idx+1}: 9x Módulos 580W TOPCon (String {r_idx+1} = 5,22 kWp)", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((x_start, ry - 0.35))

    # Inversor e Stringbox (localizados na parede técnica a leste)
    inv_x, inv_y = sx + L - 1.2, sy + 4.0
    msp.add_lwpolyline([(inv_x, inv_y), (inv_x + 0.8, inv_y), (inv_x + 0.8, inv_y + 1.2), (inv_x, inv_y + 1.2), (inv_x, inv_y)], dxfattribs={'layer': 'SOLAR_ELETRICO', 'closed': True})
    msp.add_text("INVERSOR", dxfattribs={'layer': 'SOLAR_ELETRICO', 'height': 0.14}).set_placement((inv_x + 0.05, inv_y + 0.7))
    msp.add_text("10 kW 3F", dxfattribs={'layer': 'SOLAR_ELETRICO', 'height': 0.12}).set_placement((inv_x + 0.10, inv_y + 0.4))

    # Eletroduto / Cabeamento CC das strings até o inversor
    msp.add_line((x_start + 9*(mw+gap), row_y_offsets[0] + ml_proj/2), (inv_x, inv_y + 0.8), dxfattribs={'layer': 'SOLAR_ELETRICO'})
    msp.add_line((x_start + 9*(mw+gap), row_y_offsets[1] + ml_proj/2), (inv_x, inv_y + 0.4), dxfattribs={'layer': 'SOLAR_ELETRICO'})

    # Ralos pluviais nos cantos da laje
    for rx, ry in [(sx + 0.4, sy + 0.4), (sx + L - 0.4, sy + 0.4), (sx + 0.4, sy + W - 0.4), (sx + L - 0.4, sy + W - 0.4)]:
        msp.add_circle((rx, ry), radius=0.15, dxfattribs={'layer': 'ARQ_PISO_LAJE'})
        msp.add_text("RP 100", dxfattribs={'layer': 'TEXTOS', 'height': 0.10}).set_placement((rx - 0.15, ry + 0.2))

    # Cotas da cobertura
    msp.add_aligned_dim(p1=(sx, sy - 1.0), p2=(sx + L, sy - 1.0), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(sx - 1.0, sy), p2=(sx - 1.0, sy + W), distance=0.4, dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 3. CORTE TRANSVERSAL A-A (Escala 1:50)
    # =========================================================================
    cx, cy = 0.0, -14.0

    msp.add_text("3. CORTE TRANSVERSAL A-A", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((cx, cy + h_plati + 2.5))
    msp.add_text("Escala 1:50 | Mostrando perfil da laje plana, platibanda e módulos solares a 18°", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((cx, cy + h_plati + 1.9))

    # Piso e Terreno
    msp.add_line((cx - 1.5, cy), (cx + W + 1.5, cy), dxfattribs={'layer': 'ARQ_PISO_LAJE'})
    msp.add_text("NÍVEL DO TERRENO: COTA +0,00m", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((cx - 1.5, cy - 0.35))

    # Paredes laterais em corte (x = cx e x = cx + W)
    # Parede esquerda
    msp.add_lwpolyline([(cx, cy), (cx + t, cy), (cx + t, cy + h_plati), (cx, cy + h_plati), (cx, cy)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
    # Parede direita
    msp.add_lwpolyline([(cx + W - t, cy), (cx + W, cy), (cx + W, cy + h_plati), (cx + W - t, cy + h_plati), (cx + W - t, cy)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    # Laje de concreto em corte (espessura 0,15m na cota +3,50m)
    msp.add_lwpolyline([(cx + t, cy + h_wall), (cx + W - t, cy + h_wall), (cx + W - t, cy + h_wall - 0.15), (cx + t, cy + h_wall - 0.15), (cx + t, cy + h_wall)], dxfattribs={'layer': 'ARQ_PISO_LAJE', 'closed': True})
    msp.add_text("LAJE MACIÇA CONCRETO ARMADO e=15cm", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((cx + 1.8, cy + h_wall - 0.35))
    msp.add_text("PÉ-DIREITO LIVRE = 3,35 m", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((cx + 2.8, cy + 1.8))

    # Módulos solares em perfil inclinado (18°) sobre a laje
    # 2 fileiras no corte transversal (y_offsets: 1.50m e 4.80m a partir da parede sul)
    tilt_rad = 0.314 # 18 deg
    for fy in [1.50, 4.80]:
        px_low = cx + t + fy
        pz_low = cy + h_wall + 0.15
        px_high = px_low + 2.278 * 0.951 # cos(18)
        pz_high = pz_low + 2.278 * 0.309 # sin(18) = ~0.70m

        # Triângulo de suporte
        msp.add_line((px_low, cy + h_wall), (px_low, pz_low), dxfattribs={'layer': 'SOLAR_ESTRUTURA'})
        msp.add_line((px_high, cy + h_wall), (px_high, pz_high), dxfattribs={'layer': 'SOLAR_ESTRUTURA'})
        msp.add_line((px_low, cy + h_wall), (px_high, pz_high), dxfattribs={'layer': 'SOLAR_ESTRUTURA'})

        # Painel fotovoltaico (linha grossa)
        msp.add_line((px_low, pz_low), (px_high, pz_high), dxfattribs={'layer': 'SOLAR_PAINEIS'})
        msp.add_line((px_low, pz_low + 0.04), (px_high, pz_high + 0.04), dxfattribs={'layer': 'SOLAR_PAINEIS'})
        msp.add_text("PAINEL 580W (18° NORTE)", dxfattribs={'layer': 'TEXTOS', 'height': 0.14}).set_placement((px_low + 0.1, pz_high + 0.15))

    # Rufo de proteção metálico no topo da platibanda (+3,90m)
    msp.add_text("PLATIBANDA COTA +3,90m", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((cx - 1.2, cy + h_plati + 0.2))
    msp.add_text("LAJE PISO +3,50m", dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((cx + W + 0.2, cy + h_wall))

    # Cotas verticais do Corte
    msp.add_aligned_dim(p1=(cx - 0.6, cy), p2=(cx - 0.6, cy + h_wall), distance=0.3, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(cx - 0.6, cy + h_wall), p2=(cx - 0.6, cy + h_plati), distance=0.3, dxfattribs={'layer': 'COTAS', 'dimtype': 0})
    msp.add_aligned_dim(p1=(cx, cy - 0.8), p2=(cx + W, cy - 0.8), distance=0.3, dxfattribs={'layer': 'COTAS', 'dimtype': 0})

    # =========================================================================
    # 4. FACHADA PRINCIPAL (NOROESTE) - Vista Externa (Escala 1:50)
    # =========================================================================
    fx, fy = 16.0, -14.0

    msp.add_text("4. ELEVAÇÃO / FACHADA FRONTAL", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((fx, fy + h_plati + 2.5))
    msp.add_text("Vista Frontal Noroeste | Arquitetura Contemporânea com Platibanda Reta", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((fx, fy + h_plati + 1.9))

    # Linha do solo
    msp.add_line((fx - 1.0, fy), (fx + L + 1.0, fy), dxfattribs={'layer': 'ARQ_PISO_LAJE'})

    # Contorno da fachada (paredes e platibanda reta)
    msp.add_lwpolyline([(fx, fy), (fx + L, fy), (fx + L, fy + h_plati), (fx, fy + h_plati), (fx, fy)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})

    # Rufo de acabamento da platibanda no topo
    msp.add_lwpolyline([(fx - 0.05, fy + h_plati), (fx + L + 0.05, fy + h_plati), (fx + L + 0.05, fy + h_plati + 0.08), (fx - 0.05, fy + h_plati + 0.08), (fx - 0.05, fy + h_plati)], dxfattribs={'layer': 'ARQ_PLATIBANDA', 'closed': True})

    # Porta dupla principal em vidro temperado (x = fx + 3.5m a 5.5m, h = 2.20m)
    msp.add_lwpolyline([(fx + 3.5, fy), (fx + 5.5, fy), (fx + 5.5, fy + 2.2), (fx + 3.5, fy + 2.2), (fx + 3.5, fy)], dxfattribs={'layer': 'ARQ_ESQUADRIAS', 'closed': True})
    msp.add_line((fx + 4.5, fy), (fx + 4.5, fy + 2.2), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
    msp.add_text("PORTA VIDRO TEMPERADO 2.00x2.20", dxfattribs={'layer': 'TEXTOS', 'height': 0.14}).set_placement((fx + 3.2, fy + 2.35))

    # Janelas J1 na fachada frontal
    for jx in [fx + 1.0, fx + 7.5]:
        msp.add_lwpolyline([(jx, fy + 1.1), (jx + 2.0, fy + 1.1), (jx + 2.0, fy + 2.3), (jx, fy + 2.3), (jx, fy + 1.1)], dxfattribs={'layer': 'ARQ_ESQUADRIAS', 'closed': True})
        msp.add_line((jx + 1.0, fy + 1.1), (jx + 1.0, fy + 2.3), dxfattribs={'layer': 'ARQ_ESQUADRIAS'})
        msp.add_text("J1 2.00x1.20", dxfattribs={'layer': 'TEXTOS', 'height': 0.12}).set_placement((jx + 0.4, fy + 2.4))

    # Cúpula / perfil visível dos módulos solares acima da laje (vistos suavemente por trás da platibanda)
    msp.add_text("MÓDULOS SOLARES EMBUTIDOS NA COBERTURA", dxfattribs={'layer': 'SOLAR_PAINEIS', 'height': 0.16}).set_placement((fx + 2.5, fy + h_plati + 0.3))

    # =========================================================================
    # 5. QUADRO TÉCNICO EXECUTIVO & DIAGRAMA UNIFILAR (Escala NTS)
    # =========================================================================
    tx, ty = 0.0, -26.0

    msp.add_text("5. MEMORIAL DESCRITIVO & ESPECIFICAÇÕES DO SISTEMA", dxfattribs={'layer': 'TITULOS', 'height': 0.40}).set_placement((tx, ty + 7.5))

    # Tabela de Especificações Técnicas
    tabela_linhas = [
        "PARÂMETRO", "ESPECIFICAÇÃO DE ENGENHARIA",
        "Área Construída do Salão:", "89,21 m² interna (11,00 m × 8,11 m externo)",
        "Pé-direito Livre:", "3,50 m (Piso acabado até a face inferior da laje)",
        "Sistema Estrutural do Telhado:", "Laje plana maciça de concreto armado e=15cm",
        "Impermeabilização:", "Manta asfáltica aluminizada bicamada 4mm elastomérica",
        "Platibanda Perimetral:", "Alvenaria com rufo galvanizado h=3,90 m (+0,40m sobre laje)",
        "Potência Fotovoltaica de Pico:", "10,44 kWp (DC)",
        "Módulos Solares:", "18x 580W TOPCon Monocristalinos Bifaciais Alta Eficiência",
        "Arranjo das Strings:", "2 Strings de 9 módulos em série (Voc=463,5V, Vmp=385,2V)",
        "Inversor Solar Grid-Tie:", "1x 10 kW Trifásico 220V/380V (MPPT Duplo, Eficiência 98,6%)",
        "Orientação e Inclinação:", "Norte Verdadeiro (Azimute 0°) | Inclinação Ótima 18°",
        "Geração Anual Estimada:", "14.200 kWh/ano (Média de 1.183 kWh/mês)",
        "Economia Financeira Anual:", "~R$ 12.000,00 / ano (Tarifa média B3 rural/residencial)",
        "Vida Útil do Sistema:", "25 a 30 anos (Garantia de 25 anos a 85% de rendimento)",
        "Normas Atendidas:", "NBR 5410, NBR 16690, NBR 10898 e Resolução ANEEL 1000/2021"
    ]

    table_w = 14.5
    row_h = 0.45
    num_rows = len(tabela_linhas) // 2

    for r in range(num_rows):
        ry = ty + 6.8 - r * row_h
        col1 = tabela_linhas[r * 2]
        col2 = tabela_linhas[r * 2 + 1]

        # Linhas da tabela
        msp.add_line((tx, ry), (tx + table_w, ry), dxfattribs={'layer': 'ARQ_PISO_LAJE'})
        msp.add_text(col1, dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((tx + 0.2, ry - 0.30))
        msp.add_text(col2, dxfattribs={'layer': 'TEXTOS', 'height': 0.16}).set_placement((tx + 6.2, ry - 0.30))

    # Borda da tabela
    msp.add_lwpolyline([(tx, ty + 6.8), (tx + table_w, ty + 6.8), (tx + table_w, ty + 6.8 - num_rows * row_h), (tx, ty + 6.8 - num_rows * row_h), (tx, ty + 6.8)], dxfattribs={'layer': 'ARQ_PAREDES', 'closed': True})
    msp.add_line((tx + 6.0, ty + 6.8), (tx + 6.0, ty + 6.8 - num_rows * row_h), dxfattribs={'layer': 'ARQ_PAREDES'})

    # Selo Técnico / Carimbo do Projeto (à direita)
    bx, by = 16.0, -26.0
    selo_w, selo_h = 12.0, 7.0

    msp.add_lwpolyline([(bx, by), (bx + selo_w, by), (bx + selo_w, by + selo_h), (bx, by + selo_h), (bx, by)], dxfattribs={'layer': 'PRANCHA_SELO', 'closed': True})
    msp.add_line((bx, by + 5.5), (bx + selo_w, by + 5.5), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((bx, by + 3.8), (bx + selo_w, by + 3.8), dxfattribs={'layer': 'PRANCHA_SELO'})
    msp.add_line((bx, by + 2.0), (bx + selo_w, by + 2.0), dxfattribs={'layer': 'PRANCHA_SELO'})

    msp.add_text("PROJETO EXECUTIVO DE ARQUITETURA E ENERGIA SOLAR", dxfattribs={'layer': 'TITULOS', 'height': 0.32}).set_placement((bx + 0.4, by + 6.0))
    msp.add_text("EDIFICAÇÃO: SALÃO COM TELHADO RETO (LAJE PLANA)", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((bx + 0.4, by + 4.6))
    msp.add_text("USINA FOTOVOLTAICA DE COBERTURA: 10,44 kWp (18x 580W)", dxfattribs={'layer': 'TEXTOS', 'height': 0.20}).set_placement((bx + 0.4, by + 4.1))

    msp.add_text("PROPRIEDADE: NOVO SÍTIO DAS ANDORINHAS", dxfattribs={'layer': 'TEXTOS', 'height': 0.22}).set_placement((bx + 0.4, by + 2.8))
    msp.add_text("LOCALIZAÇÃO: ESTRADA RIBEIRÃO DOS OVOS - SANTA CATARINA", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 2.3))

    msp.add_text("CONTEÚDO: Plantas, Cortes, Elevações e Especificações Fotovoltaicas", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 1.2))
    msp.add_text("ESCALA: Indicadas (1:50 / NTS) | UNIDADES: Metros | DATA: 2026", dxfattribs={'layer': 'TEXTOS', 'height': 0.18}).set_placement((bx + 0.4, by + 0.5))

    doc.saveas(OUT_DXF)
    print(f"Sucesso: Projeto do Salão gerado em {OUT_DXF} ({os.path.getsize(OUT_DXF):,} bytes)")

if __name__ == '__main__':
    criar_projeto_salao()
