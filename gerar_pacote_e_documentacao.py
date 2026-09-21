#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o Memorial Descritivo de Engenharia Solar (em Markdown e HTML formatado)
e empacota todo o projeto em um arquivo ZIP para entrega ao engenheiro.
"""

import os
import zipfile

SOLAR_DIR = r"C:\Users\haas\github\solar"
MD_OUT = os.path.join(SOLAR_DIR, "MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.md")
HTML_OUT = os.path.join(SOLAR_DIR, "MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.html")
TXT_OUT = os.path.join(SOLAR_DIR, "README_ENGENHEIRO.txt")
ZIP_OUT = os.path.join(SOLAR_DIR, "Pacote_Engenharia_Solar_Sitio_das_Andorinhas.zip")

KMZ_MASTER = os.path.join(SOLAR_DIR, "Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz")
HTML_3D = os.path.join(SOLAR_DIR, "visualizador_3d_sitio.html")
KMZ_ORTHO = os.path.join(SOLAR_DIR, "Estrada-Ribeiro-dos-Ovos-01-06-2024-orthophoto_1.kmz")
KMZ_SOLAR = os.path.join(SOLAR_DIR, "Simulacao_Carta_Solar_3D.kmz")

def gerar_memorial_md():
    md = """# MEMORIAL DESCRITIVO E DIRETRIZES DE ENGENHARIA
## COMPLEXO FOTOVOLTAICO SÍTIO DAS ANDORINHAS (~1,90 MWp)
**Propriedade:** Sítio das Andorinhas | Estrada Ribeirão dos Ovos  
**Município:** Santa Catarina, Brasil  
**Coordenadas Geográficas Centrais:** Latitude: -27,3957° S | Longitude: -49,3468° O | Fuso Horário: UTC-3  
**Data do Relatório:** Setembro de 2026  

---

## 1. INTRODUÇÃO E OBJETIVO DO PROJETO

Este documento consolida o projeto conceitual e executivo do **Complexo Solar Sítio das Andorinhas**, totalizando **1.902,40 kWp (~1,90 MWp)** de potência instalada em corrente contínua (DC).

O projeto foi integralmente concebido e modelado com base em:
1. **Modelo Digital de Terreno (MDT) LiDAR do SIGSC Nativo**, com resolução espacial de **1,0 metro** e mais de 1,37 milhão de vértices altimétricos reais, garantindo a modelagem fidedigna de cada curva de nível e declividade natural do solo.
2. **Ortofotogrametria Aérea por Drone em Alta Resolução**, assegurando o georreferenciamento milimétrico em relação à malha viária, benfeitorias, linhas de transmissão e divisas da propriedade.
3. **Engenharia de Otimização Fotovoltaica para o Hemisfério Sul**, adotando azimute **0° (Norte Verdadeiro)** e inclinação otimizada para maximização da produção anual e minimização de sombreamento mútuo entre fileiras.

---

## 2. QUADRO GERAL DE CARGAS E ESTRUTURAS FOTOVOLTAICAS

| Setor da Usina | Tipo de Estrutura | Quantidade de Mesas / Arranjos | Quantidade de Módulos (580W) | Potência Instalada (kWp) | Geração Anual Estimada (MWh) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **UFV Solo - Setor P1** | Mesas Solo 2P × 7 | 114 mesas | 1.596 módulos | **925,68 kWp** | ~1.258,9 MWh/ano |
| **UFV Solo - Setor P2** | Mesas Solo 2P × 7 | 73 mesas | 1.022 módulos | **592,76 kWp** | ~806,2 MWh/ano |
| **UFV Solo - Setor P3** | Mesas Solo 2P × 7 | 46 mesas | 644 módulos | **373,52 kWp** | ~508,0 MWh/ano |
| **Salão de Eventos** | Cobertura Laje Reto | 2 arranjos × 9 | 18 módulos | **10,44 kWp** | ~14,2 MWh/ano |
| **TOTAL DO COMPLEXO** | **Solo + Cobertura** | **233 mesas + cob.** | **3.280 módulos** | **1.902,40 kWp (~1,90 MWp)** | **~2.587,3 MWh/ano** |

### Especificações das Mesas e Módulos Fotovoltaicos:
- **Tecnologia dos Módulos:** Módulos fotovoltaicos monocristalinos bifaciais de alta eficiência de **580 Wp**.
- **Configuração de Mesa Solo:** Estruturas bifaciais fixas tipo 2P (2 módulos em retrato × 7 colunas = 14 módulos por mesa), com 8,00 m de largura e 4,05 m de comprimento inclinado.
- **Estruturas de Solo:** Fixação por estacas de aço cravadas no solo (relativeToGround), adaptando-se às cotas naturais do relevo.
- **Salão de Eventos:** Edificação com telhado plano e platibanda de proteção, abrigando 18 módulos fotovoltaicos com suportes de inclinação a 18° Norte.
- **Área Esportiva Adjacente:** Campo de futebol e vôlei de areia (22,0 m × 12,0 m) com redes de proteção 3D perimetrais e superiores de 6,0 m de altura.

---

## 3. GEOMETRIA SOLAR, ORIENTAÇÃO E SOMBREAMENTO

### 3.1. Orientação Azimutal (Norte Verdadeiro)
Localizado a **Latitude -27,3957° S**, o complexo solar está situado abaixo do Trópico de Capricórnio. A trajetória do sol ao meio-dia solar ao longo de todo o ano ocorre no quadrante **Norte**.
- **Azimute Adotado:** **0° (Norte Verdadeiro)** para todas as 233 mesas de solo e usina do salão.
- **Sentido de Inclinação:** Bordo inferior (dianteiro) voltado para o **Norte** ($Z = 0,60\\text{ m}$) e bordo superior (traseiro) elevado para o **Sul** ($Z = 2,15\\text{ m}$).
- **Ângulo de Inclinação de Solo:** **20°** em relação ao plano horizontal.
- **Ângulo de Inclinação da Cobertura:** **18°** em relação ao plano da laje.

### 3.2. Análise Crítica de Sombreamento (Solstício de Inverno - 21 de Junho)
- No **Solstício de Inverno (21/Jun)**, a declinação solar atinge $+23,45°$, resultando na menor altura solar do ano: **39,15° ao meio-dia solar**.
- O comprimento da sombra projetada no solo é de aproximadamente **$1,23 \\times$ a altura da mesa** ($L = H / \\tan(39,15°)$).
- O pitch (distância entre eixos de fileiras) adotado de **9,0 a 10,0 metros** garante **sombreamento mútuo zero** no intervalo crítico das 09:30 às 14:30.
- No **Equinócio (21/Mar e 22/Set)**, o sol atinge **62,6°**, e a incidência solar direta é **99,2% perpendicular** à face dos módulos.
- No **Solstício de Verão (21/Dez)**, o sol atinge **84,7°** (quase o zênite), com sombra mínima de apenas $0,09 \\times$ a altura.

---

## 4. SISTEMAS DE VISUALIZAÇÃO E SIMULAÇÃO ENTREGUES

Foram desenvolvidas **duas plataformas complementares e independentes** para a avaliação técnica do engenheiro:

### OPÇÃO 1: Visualizador 3D Interativo WebGL (`visualizador_3d_sitio.html`)
- **Compatibilidade:** Abre diretamente em qualquer navegador moderno (Chrome, Edge, Firefox, Safari) em qualquer computador (Windows, Mac, Linux). Não requer instalação de programas.
- **Recursos Principais:**
  1. **☀️ Botão de Ocultar/Exibir Painéis Solares:** Permite desligar instantaneamente todas as mesas fotovoltaicas com um clique para inspeção direta do terreno, curvas de nível e estradas de acesso.
  2. **☀️ Simulador Solar Anual & Diário Integrado:**
     - **Controle Anual:** Seletor de dia do ano (1 a 365) com botões de atalho para Solstício de Verão, Solstício de Inverno e Equinócios.
     - **Controle Diário:** Controle deslizante de horário solar (05:30 às 18:30) com botão **▶️ Simular Dia** para animação solar contínua.
     - **Sombreamento Dinâmico Físico:** Motor de sombras Three.js PCF Soft Shadow que projeta as sombras reais das mesas e do relevo em tempo real.
     - **Telemetria Solar em Tempo Real:** Mostra a qualquer instante a altitude solar exata, o azimute em graus e rosa dos ventos, e a razão de projeção de sombra.
     - **Representação Visual do Sol:** Esfera solar tridimensional navegando na abóbada celeste e alterando o tom do céu (aurora, zênite, crepúsculo).
  3. **Malha LiDAR 1,0 m (Wireframe):** Alternador para visualização da malha estrutural de 1 vértice por metro.
  4. **Foco Automatizado por Setor:** Botões de câmera para inspeção detalhada de P1, P2, P3 e Salão.

### OPÇÃO 2: Projeto Solar Completo no Google Earth (`Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz`)
- **Compatibilidade:** Google Earth Pro (Desktop) e Google Earth Web.
- **Recursos Principais:**
  1. **Ficha Técnica e Resumo Executivo Completo:** Pin interativo com tabela de dados técnicos e energéticos de ~1,90 MWp.
  2. **Divisão e Limites do Sítio:** Perímetro de 18,60 ha e setores P1, P2 e P3 colados com alta precisão no terreno (`clampToGround` com tesselação contínua).
  3. **Modelagem 3D das Usinas:** 233 mesas de solo com pés cravados e salão de eventos modelado com cobertura solar.
  4. **Simulação e Carta Solar 3D:**
     - **Arcos Solares Celestes Tridimensionais:** Trajetórias celestes completas do Sol no Solstício de Verão (~85°), Equinócios (~63°) e Solstício de Inverno (~39°).
     - **Marcadores Horários:** Balões de dados técnicos a cada 2 horas com altitude, azimute, rendimento de incidência angular e multiplicador de sombra.
     - **Integração com Sol Nativo do Google Earth:** Instruções passo a passo para ativar o recurso `Visualizar -> Sol` no Google Earth Pro e simular as sombras dinâmicas no relevo 3D.
  5. **Ortofoto do Drone de Alta Resolução:** Imagem real georreferenciada via NetworkLink de alta velocidade.
  6. **Limpeza Visual Total:** Nenhuma linha de voo ou estações de foto poluindo a visualização.

---

## 5. LOCALIZAÇÃO DOS ARQUIVOS E INSTRUÇÕES DE ACESSO

Todos os arquivos estão organizados no diretório do projeto e empacotados no arquivo compactado:
**`C:\\Users\\haas\\github\\solar\\Pacote_Engenharia_Solar_Sitio_das_Andorinhas.zip`**

### Conteúdo do Pacote:
1. `Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz` (Arquivo principal Google Earth)
2. `visualizador_3d_sitio.html` (Visualizador 3D independente para navegador)
3. `Simulacao_Carta_Solar_3D.kmz` (Carta Solar 3D avulsa)
4. `projeto_solar_p1.kmz`, `projeto_solar_p2.kmz`, `projeto_solar_p3.kmz` (Setores individuais)
5. `salao_telhado_reto_com_solar.kmz` (Salão de eventos individual)
6. `Divisao_Sitio_das_Andorinhas.kmz` (Limites e áreas úteis)
7. `MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.html` (Relatório técnico formatado para impressão/PDF)
8. `MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.md` (Documento técnico em Markdown)
9. `README_ENGENHEIRO.txt` (Guia rápido de utilização)

---
*Relatório de Engenharia Fotovoltaica e Cartográfica — Sítio das Andorinhas.*
"""
    with open(MD_OUT, 'w', encoding='utf-8') as f:
        f.write(md)
    print(f"Memorial Markdown salvo: {MD_OUT}")
    return md

def gerar_memorial_html(md_text):
    # Converter Markdown simples para HTML elegante
    import re
    
    html_body = md_text
    # Títulos
    html_body = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', html_body, flags=re.M)
    html_body = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', html_body, flags=re.M)
    html_body = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', html_body, flags=re.M)
    # Negrito e Itálico
    html_body = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html_body)
    html_body = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html_body)
    # Listas
    html_body = re.sub(r'^- (.*?)$', r'<li>\1</li>', html_body, flags=re.M)
    html_body = re.sub(r'((?:<li>.*?</li>\n?)+)', r'<ul>\1</ul>', html_body)
    # Código
    html_body = re.sub(r'`(.*?)`', r'<code>\1</code>', html_body)
    # Linhas Horizontais
    html_body = re.sub(r'^---$', r'<hr/>', html_body, flags=re.M)
    
    # Tabelas
    lines = html_body.splitlines()
    in_table = False
    new_lines = []
    for l in lines:
        if l.strip().startswith('|') and l.strip().endswith('|'):
            if not in_table:
                in_table = True
                new_lines.append('<table class="tech-table">')
            cells = [c.strip() for c in l.strip()[1:-1].split('|')]
            if ':---' in cells[0] or '---' in cells[0]:
                continue
            is_header = ('Setor da Usina' in cells[0] or 'UFV' not in cells[0] and not any('kWp' in c for c in cells))
            tag = 'th' if is_header else 'td'
            row_html = '<tr>' + ''.join([f'<{tag}>{c}</{tag}>' for c in cells]) + '</tr>'
            new_lines.append(row_html)
        else:
            if in_table:
                in_table = False
                new_lines.append('</table>')
            new_lines.append(l)
    if in_table:
        new_lines.append('</table>')
    html_body = '\n'.join(new_lines)
    
    # Parágrafos
    html_body = re.sub(r'\n\n([^<].*?)\n\n', r'\n\n<p>\1</p>\n\n', html_body)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Memorial Descritivo — Complexo Fotovoltaico Sítio das Andorinhas (~1,90 MWp)</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      line-height: 1.6;
      color: #1e293b;
      max-width: 960px;
      margin: 40px auto;
      padding: 0 30px;
      background: #f8fafc;
    }}
    .document-card {{
      background: #ffffff;
      padding: 45px 55px;
      border-radius: 12px;
      box-shadow: 0 4px 25px rgba(0,0,0,0.07);
      border: 1px solid #e2e8f0;
    }}
    h1 {{
      color: #0369a1;
      font-size: 24px;
      margin-bottom: 4px;
      border-bottom: 3px solid #0284c7;
      padding-bottom: 10px;
    }}
    h2 {{
      color: #0f172a;
      font-size: 18px;
      margin-top: 28px;
      margin-bottom: 12px;
      border-bottom: 1px solid #cbd5e1;
      padding-bottom: 6px;
    }}
    h3 {{
      color: #0284c7;
      font-size: 15px;
      margin-top: 20px;
      margin-bottom: 8px;
    }}
    p {{
      margin-bottom: 12px;
      font-size: 14.5px;
      color: #334155;
    }}
    ul, ol {{
      margin-left: 24px;
      margin-bottom: 14px;
      font-size: 14px;
      color: #334155;
    }}
    li {{
      margin-bottom: 6px;
    }}
    hr {{
      border: 0;
      border-top: 1px solid #e2e8f0;
      margin: 24px 0;
    }}
    code {{
      background: #f1f5f9;
      color: #0369a1;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: Consolas, monospace;
      font-size: 13.5px;
    }}
    .tech-table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      font-size: 13.5px;
    }}
    .tech-table th {{
      background: #0284c7;
      color: white;
      padding: 10px 12px;
      text-align: left;
      font-weight: 600;
      border: 1px solid #0369a1;
    }}
    .tech-table td {{
      padding: 8px 12px;
      border: 1px solid #e2e8f0;
      color: #1e293b;
    }}
    .tech-table tr:nth-child(even) {{
      background: #f8fafc;
    }}
    .tech-table tr:last-child {{
      background: #f0fdf4;
      font-weight: 700;
    }}
    .print-btn {{
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #0284c7;
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 8px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(2, 132, 199, 0.4);
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .print-btn:hover {{
      background: #0369a1;
    }}
    @media print {{
      body {{ background: white; margin: 0; padding: 0; }}
      .document-card {{ box-shadow: none; border: none; padding: 0; }}
      .print-btn {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="document-card">
    {html_body}
  </div>
  <button class="print-btn" onclick="window.print()">🖨️ Imprimir / Salvar como PDF</button>
</body>
</html>"""
    with open(HTML_OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Memorial HTML salvo: {HTML_OUT}")

def gerar_readme_engenheiro():
    txt = """================================================================================
COMPLEXO SOLAR SÍTIO DAS ANDORINHAS (~1,90 MWp)
PACOTE DE ENGENHARIA E DIRETRIZES TÉCNICAS
================================================================================

Prezado Engenheiro,

Este pacote reúne o projeto executivo e conceitual completo da usina fotovoltaica
de ~1,90 MWp (1.902,40 kWp) projetada para o Sítio das Andorinhas, integrando:
- Topografia LiDAR de alta precisão (1,0 m) do SIGSC (1,37 milhão de cotas).
- Ortofotometria aérea HD capturada por Drone.
- 233 Mesas fotovoltaicas de solo (P1, P2, P3) e cobertura do Salão.
- Orientação para o Norte Verdadeiro (Azimute 0°, inclinação 20° solo e 18° teto).
- Simulador Solar Diário e Anual nos dois sistemas.

--------------------------------------------------------------------------------
COMO UTILIZAR AS DUAS OPÇÕES DE ENTREGA:
--------------------------------------------------------------------------------

OPÇÃO 1: VISUALIZADOR 3D INTERATIVO NO NAVEGADOR
Arquivo: visualizador_3d_sitio.html
- Como abrir: Dê um duplo-clique no arquivo "visualizador_3d_sitio.html".
  Ele abre imediatamente no Google Chrome, Microsoft Edge ou Firefox sem precisar
  instalar nada.
- Recursos disponíveis:
  * ☀️ Botão "Ocultar Painéis Solares": oculta/exibe as usinas solares com 1 clique
    para você inspecionar o terreno limpo por baixo.
  * ☀️ Simulador Solar Anual e Diário:
    - Controle a data do ano (Solstício de Verão, Solstício de Inverno, Equinócios).
    - Controle a hora do dia (05:30 às 18:30) ou clique em "▶️ Simular Dia".
    - Veja a sombra dinâmica das mesas se movimentando em tempo real sobre o relevo!
    - Acompanhe a telemetria em tempo real: altitude solar, azimute e razão de sombra.
  * ⚡ Malha LiDAR 1,0 m (Wireframe): veja a rede triangular tridimensional real.
  * 🔎 Foco por Setor: P1 (114 mesas), P2 (73 mesas), P3 (46 mesas) e Salão.

OPÇÃO 2: GOOGLE EARTH PRO (DESKTOP E WEB)
Arquivo: Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz
- Como abrir: Abra o arquivo no Google Earth Pro (desktop) ou earth.google.com (web).
- Recursos disponíveis:
  * Ficha Técnica / Resumo Executivo em cada setor fotovoltaico.
  * Linhas perimetrais e divisas do sítio (18,60 ha) coladas no terreno (3D real).
  * 233 Mesas modeladas com pés cravados no solo na cota exata do terreno.
  * Carta Solar 3D com as trajetórias celestes completas do Sol no Solstício de
    Verão (~85°), Equinócios (~63°) e Solstício de Inverno (~39°), com esferas a cada 2h.
  * SIMULAÇÃO DE SOL E SOMBRAS NATIVO:
    No menu do Google Earth Pro, clique em "Visualizar -> Sol" (ou Ctrl + Alt + S).
    A barra de tempo permitirá simular a projeção solar real sobre o complexo!
  * Ortofoto de drone em alta resolução limpa (sem linhas de voo).

--------------------------------------------------------------------------------
DOCUMENTAÇÃO DE ENGENHARIA ANEXA:
--------------------------------------------------------------------------------
- MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.html: Relatório técnico completo formatado,
  pronto para impressão ou exportação para PDF pelo navegador.
- MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.md: Relatório técnico em Markdown.

--------------------------------------------------------------------------------
ONDE ENCONTRAR O PACOTE NO COMPUTADOR:
C:\\Users\\haas\\github\\solar\\Pacote_Engenharia_Solar_Sitio_das_Andorinhas.zip
================================================================================
"""
    with open(TXT_OUT, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f"README Engenheiro salvo: {TXT_OUT}")

def empacotar_zip():
    print("Empacotando projeto em ZIP...")
    files_to_pack = [
        ("Projeto_Solar_Completo_Sitio_das_Andorinhas.kmz", KMZ_MASTER),
        ("visualizador_3d_sitio.html", HTML_3D),
        ("Simulacao_Carta_Solar_3D.kmz", KMZ_SOLAR),
        ("projeto_solar_p1.kmz", os.path.join(SOLAR_DIR, "projeto_solar_p1.kmz")),
        ("projeto_solar_p2.kmz", os.path.join(SOLAR_DIR, "projeto_solar_p2.kmz")),
        ("projeto_solar_p3.kmz", os.path.join(SOLAR_DIR, "projeto_solar_p3.kmz")),
        ("salao_telhado_reto_com_solar.kmz", os.path.join(SOLAR_DIR, "salao_telhado_reto_com_solar.kmz")),
        ("Campo_de_areia_modelado_com_redes.kmz", os.path.join(SOLAR_DIR, "Campo_de_areia_modelado_com_redes.kmz")),
        ("Divisao_Sitio_das_Andorinhas.kmz", os.path.join(SOLAR_DIR, "Divisao_Sitio_das_Andorinhas.kmz")),
        ("MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.html", HTML_OUT),
        ("MEMORIAL_DESCRITIVO_ENGENHARIA_SOLAR.md", MD_OUT),
        ("README_ENGENHEIRO.txt", TXT_OUT)
    ]
    
    with zipfile.ZipFile(ZIP_OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        for arcname, filepath in files_to_pack:
            if os.path.exists(filepath):
                z.write(filepath, arcname)
                sz_kb = os.path.getsize(filepath) / 1024
                print(f"  + Adicionado ao ZIP: {arcname} ({sz_kb:.1f} KB)")
            else:
                print(f"  ! Arquivo não encontrado: {filepath}")

    sz_mb = os.path.getsize(ZIP_OUT) / (1024 * 1024)
    print(f"\nPACOTE ZIP GERADO COM SUCESSO: {ZIP_OUT} ({sz_mb:.2f} MB)")

def main():
    md = gerar_memorial_md()
    gerar_memorial_html(md)
    gerar_readme_engenheiro()
    empacotar_zip()

if __name__ == '__main__':
    main()
