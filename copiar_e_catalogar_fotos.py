import os
import shutil
import json
import pandas as pd
import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS

SOLAR_DIR = r"C:\Users\haas\github\solar"
CAT_CSV = os.path.join(SOLAR_DIR, "catalogo_fotos_drone_2026.csv")
TARGET_DIR = os.path.join(SOLAR_DIR, "fotos_drone_local_projeto")
OVERHEAD_DIR = os.path.join(TARGET_DIR, "direto_em_cima_do_complexo")
NEAR_DIR = os.path.join(TARGET_DIR, "entorno_imediato_ate_50m")

os.makedirs(OVERHEAD_DIR, exist_ok=True)
os.makedirs(NEAR_DIR, exist_ok=True)

DRONE_ROOTS = [r"E:\drone\DCIM", r"D:\drone\DCIM"]

# Coordinates
lat_s, lon_s = -27.3956822, -49.3468823 # Salão
lat_c, lon_c = -27.3957344, -49.3467864 # Centro Complexo Salão+Campo

df = pd.read_csv(CAT_CSV)

# Calculate metric distances
dy_s = (df['lat'] - lat_s) * 111139.0
dx_s = (df['lon'] - lon_s) * (111139.0 * np.cos(np.radians(lat_s)))
df['dist_salao'] = np.sqrt(dx_s**2 + dy_s**2)

dy_c = (df['lat'] - lat_c) * 111139.0
dx_c = (df['lon'] - lon_c) * (111139.0 * np.cos(np.radians(lat_c)))
df['dist_campo'] = np.sqrt(dx_c**2 + dy_c**2)

df['min_dist'] = np.minimum(df['dist_salao'], df['dist_campo'])
df['rel_alt_solo'] = df['alt'] - 547.32 # Solo está na cota ~547m

print(f"Total de fotos no catálogo 2026: {len(df)}")
print(f"Fotos diretamente em cima (<= 25m): {len(df[df['min_dist'] <= 25])}")
print(f"Fotos no entorno imediato (<= 50m): {len(df[df['min_dist'] <= 50])}")

# Function to extract DJI XMP metadata
def get_dji_xmp(filepath):
    meta = {}
    try:
        with open(filepath, 'rb') as f:
            content = f.read(150000)
            idx = content.find(b'<x:xmpmeta')
            if idx != -1:
                end = content.find(b'</x:xmpmeta>', idx)
                xmp_str = content[idx:end+12].decode('utf-8', errors='ignore')
                for line in xmp_str.split('\n'):
                    for k in ['RelativeAltitude', 'AbsoluteAltitude', 'GimbalPitchDegree', 'FlightYawDegree']:
                        tag = f'drone-dji:{k}="'
                        if tag in line:
                            val = line.split(tag)[1].split('"')[0]
                            meta[k] = float(val)
    except Exception as e:
        pass
    return meta

overhead_records = []
near_records = []

# Process directly overhead photos (<= 25m)
overhead_df = df[df['min_dist'] <= 25].sort_values('min_dist')

copied_overhead = 0
for idx, row in overhead_df.iterrows():
    folder = row['folder']
    fname = row['file']
    rel_path = os.path.join(folder, fname)
    
    src_file = None
    for r in DRONE_ROOTS:
        cand = os.path.join(r, rel_path)
        if os.path.exists(cand):
            src_file = cand
            break
            
    if src_file:
        dst_name = f"{folder}_{fname}"
        dst_path = os.path.join(OVERHEAD_DIR, dst_name)
        if not os.path.exists(dst_path) or os.path.getsize(dst_path) != os.path.getsize(src_file):
            shutil.copy2(src_file, dst_path)
            copied_overhead += 1
            
        xmp = get_dji_xmp(src_file)
        overhead_records.append({
            'filename': dst_name,
            'original_folder': folder,
            'original_file': fname,
            'dist_salao_m': round(float(row['dist_salao']), 2),
            'dist_campo_m': round(float(row['dist_campo']), 2),
            'min_dist_m': round(float(row['min_dist']), 2),
            'lat': float(row['lat']),
            'lon': float(row['lon']),
            'alt_ellipsoid_m': round(float(row['alt']), 2),
            'rel_alt_solo_m': round(float(row['rel_alt_solo']), 2),
            'dji_rel_alt_m': xmp.get('RelativeAltitude', round(float(row['rel_alt_solo']), 2)),
            'gimbal_pitch_deg': xmp.get('GimbalPitchDegree', None),
            'yaw_deg': xmp.get('FlightYawDegree', None),
            'datetime': str(row['dt'])
        })

print(f"Fotos copiadas para 'direto_em_cima_do_complexo': {copied_overhead} (Total no diretório: {len(overhead_records)})")

# Process near photos (25m < min_dist <= 50m)
near_df = df[(df['min_dist'] > 25) & (df['min_dist'] <= 50)].sort_values('min_dist')
copied_near = 0
for idx, row in near_df.iterrows():
    folder = row['folder']
    fname = row['file']
    rel_path = os.path.join(folder, fname)
    
    src_file = None
    for r in DRONE_ROOTS:
        cand = os.path.join(r, rel_path)
        if os.path.exists(cand):
            src_file = cand
            break
            
    if src_file:
        dst_name = f"{folder}_{fname}"
        dst_path = os.path.join(NEAR_DIR, dst_name)
        if not os.path.exists(dst_path) or os.path.getsize(dst_path) != os.path.getsize(src_file):
            shutil.copy2(src_file, dst_path)
            copied_near += 1
            
        xmp = get_dji_xmp(src_file)
        near_records.append({
            'filename': dst_name,
            'original_folder': folder,
            'original_file': fname,
            'dist_salao_m': round(float(row['dist_salao']), 2),
            'dist_campo_m': round(float(row['dist_campo']), 2),
            'min_dist_m': round(float(row['min_dist']), 2),
            'lat': float(row['lat']),
            'lon': float(row['lon']),
            'alt_ellipsoid_m': round(float(row['alt']), 2),
            'rel_alt_solo_m': round(float(row['rel_alt_solo']), 2),
            'dji_rel_alt_m': xmp.get('RelativeAltitude', round(float(row['rel_alt_solo']), 2)),
            'gimbal_pitch_deg': xmp.get('GimbalPitchDegree', None),
            'yaw_deg': xmp.get('FlightYawDegree', None),
            'datetime': str(row['dt'])
        })

print(f"Fotos copiadas para 'entorno_imediato_ate_50m': {copied_near} (Total no diretório: {len(near_records)})")

# Save detailed catalogs
df_over = pd.DataFrame(overhead_records)
df_over.to_csv(os.path.join(TARGET_DIR, "catalogo_fotos_direto_em_cima.csv"), index=False, encoding='utf-8-sig')

df_near = pd.DataFrame(near_records)
df_near.to_csv(os.path.join(TARGET_DIR, "catalogo_fotos_entorno_50m.csv"), index=False, encoding='utf-8-sig')

with open(os.path.join(TARGET_DIR, "catalogo_fotos_direto_em_cima.json"), 'w', encoding='utf-8') as f:
    json.dump(overhead_records, f, indent=2, ensure_ascii=False)

print("Catálogos CSV e JSON salvos com sucesso!")
