# MEMORIAL DESCRITIVO E DIRETRIZES DE ENGENHARIA
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
- **Sentido de Inclinação:** Bordo inferior (dianteiro) voltado para o **Norte** ($Z = 0,60\text{ m}$) e bordo superior (traseiro) elevado para o **Sul** ($Z = 2,15\text{ m}$).
- **Ângulo de Inclinação de Solo:** **20°** em relação ao plano horizontal.
- **Ângulo de Inclinação da Cobertura:** **18°** em relação ao plano da laje.

### 3.2. Análise Crítica de Sombreamento (Solstício de Inverno - 21 de Junho)
- No **Solstício de Inverno (21/Jun)**, a declinação solar atinge $+23,45°$, resultando na menor altura solar do ano: **39,15° ao meio-dia solar**.
- O comprimento da sombra projetada no solo é de aproximadamente **$1,23 \times$ a altura da mesa** ($L = H / \tan(39,15°)$).
- O pitch (distância entre eixos de fileiras) adotado de **9,0 a 10,0 metros** garante **sombreamento mútuo zero** no intervalo crítico das 09:30 às 14:30.
- No **Equinócio (21/Mar e 22/Set)**, o sol atinge **62,6°**, e a incidência solar direta é **99,2% perpendicular** à face dos módulos.
- No **Solstício de Verão (21/Dez)**, o sol atinge **84,7°** (quase o zênite), com sombra mínima de apenas $0,09 \times$ a altura.

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
**`C:\Users\haas\github\solar\Pacote_Engenharia_Solar_Sitio_das_Andorinhas.zip`**

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
