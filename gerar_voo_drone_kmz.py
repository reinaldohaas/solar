#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera o KMZ com as estações de câmera e trajetórias de voo do Drone (01/03/2026)
para as 2.161 fotos cobrindo o Sítio das Andorinhas.
"""

import os
import csv
import zipfile

CSV_PATH = r"C:\Users\haas\github\solar\catalogo_fotos_drone_2026.csv"
KMZ_OUT = r"C:\Users\haas\github\solar\Voo_Drone_2026_Sitio_das_Andorinhas.kmz"

def main():
    rows = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    by_folder = {}
    for r in rows:
        by_folder.setdefault(r['folder'], []).append(r)

    kml = []
    kml.append('<?xml version="1.0" encoding="UTF-8"?>')
    kml.append('<kml xmlns="http://www.opengis.net/kml/2.2">')
    kml.append('<Document>')
    kml.append('  <name>Voo de Drone 2026 - Sítio das Andorinhas (2.161 Fotos)</name>')
    kml.append('  <open>0</open>')
    kml.append('''
  <Style id="station_109">
    <IconStyle>
      <scale>0.6</scale>
      <color>ff00aaff</color>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><scale>0</scale></LabelStyle>
  </Style>
  <Style id="station_110">
    <IconStyle>
      <scale>0.7</scale>
      <color>ffff00ff</color>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><scale>0</scale></LabelStyle>
  </Style>
  <Style id="station_111">
    <IconStyle>
      <scale>0.6</scale>
      <color>ffffff00</color>
      <Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon>
    </IconStyle>
    <LabelStyle><scale>0</scale></LabelStyle>
  </Style>
  <Style id="path_109">
    <LineStyle><color>cc00aaff</color><width>2.5</width></LineStyle>
  </Style>
  <Style id="path_110">
    <LineStyle><color>ccff00ff</color><width>3.0</width></LineStyle>
  </Style>
  <Style id="path_111">
    <LineStyle><color>ccffff00</color><width>2.5</width></LineStyle>
  </Style>
''')

    folder_desc = {
        '109MEDIA': ('Voo Setor Geral / Acesso e Colina P1/P2/P3', 'station_109', 'path_109'),
        '110MEDIA': ('Voo Detalhado Salão e Campo de Areia (Close-up)', 'station_110', 'path_110'),
        '111MEDIA': ('Voo Setor Leste e Pastagem', 'station_111', 'path_111')
    }

    for folder_name, (f_label, style_station, style_path) in folder_desc.items():
        f_rows = by_folder.get(folder_name, [])
        if not f_rows:
            continue
        
        alts = [float(r['alt']) for r in f_rows]
        min_alt, max_alt = min(alts), max(alts)
        dt_start, dt_end = f_rows[0]['dt'], f_rows[-1]['dt']
        
        kml.append('  <Folder>')
        kml.append(f'    <name>{folder_name}: {f_label} ({len(f_rows)} fotos)</name>')
        kml.append('    <description><![CDATA[')
        kml.append(f'      <b>Pasta:</b> {folder_name}<br>')
        kml.append(f'      <b>Descrição:</b> {f_label}<br>')
        kml.append(f'      <b>Quantidade de Fotos:</b> {len(f_rows)}<br>')
        kml.append(f'      <b>Período:</b> {dt_start} até {dt_end}<br>')
        kml.append(f'      <b>Altitude GPS (MSL):</b> {min_alt:.1f} m a {max_alt:.1f} m<br>')
        kml.append('    ]]></description>')
        
        # Trajetórias de voo removidas conforme solicitado (apenas estações de fotos preservadas)
        
        # Subpasta de estações de câmera
        kml.append('    <Folder>')
        kml.append(f'      <name>Estações de Câmera ({len(f_rows)} fotos)</name>')
        kml.append('      <visibility>0</visibility>') # Inicia colapsado/desligado para navegação suave
        for r in f_rows:
            kml.append('      <Placemark>')
            kml.append(f'        <name>{r["file"]}</name>')
            kml.append(f'        <styleUrl>#{style_station}</styleUrl>')
            kml.append('        <description><![CDATA[')
            kml.append(f'          <b>Arquivo:</b> {r["file"]}<br>')
            kml.append(f'          <b>Pasta:</b> {r["folder"]}<br>')
            kml.append(f'          <b>Caminho Completo:</b> {r["path"]}<br>')
            kml.append(f'          <b>Data/Hora:</b> {r["dt"]}<br>')
            kml.append(f'          <b>Coordenadas:</b> {float(r["lat"]):.6f}°, {float(r["lon"]):.6f}°<br>')
            kml.append(f'          <b>Altitude GPS:</b> {float(r["alt"]):.1f} m<br>')
            kml.append('        ]]></description>')
            kml.append('        <Point>')
            kml.append('          <altitudeMode>absolute</altitudeMode>')
            kml.append(f'          <coordinates>{r["lon"]},{r["lat"]},{r["alt"]}</coordinates>')
            kml.append('        </Point>')
            kml.append('      </Placemark>')
        kml.append('    </Folder>')
        kml.append('  </Folder>')

    kml.append('</Document>')
    kml.append('</kml>')

    with zipfile.ZipFile(KMZ_OUT, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml', '\n'.join(kml).encode('utf-8'))

    print(f"KMZ gerado com sucesso: {KMZ_OUT} ({len(rows)} fotos)")

if __name__ == '__main__':
    main()
