import os
import glob
import pandas as pd
import numpy as np

# Let's inspect all photos in 109MEDIA, 110MEDIA, 111MEDIA that are close to complex
cx_lat, cx_lon = -27.39587, -49.34734
root = r"E:\drone\DCIM"

# Read XMP from files
def get_info(fpath):
    rel_alt = None
    gimbal_pitch = None
    gimbal_yaw = None
    try:
        with open(fpath, 'rb') as f:
            s = f.read(65536).decode('latin-1', errors='ignore')
            for tag in ['RelativeAltitude="', 'drone-dji:RelativeAltitude="']:
                if tag in s:
                    p = s.find(tag) + len(tag)
                    rel_alt = float(s[p:s.find('"', p)])
                    break
            for tag in ['GimbalPitchDegree="', 'drone-dji:GimbalPitchDegree="']:
                if tag in s:
                    p = s.find(tag) + len(tag)
                    gimbal_pitch = float(s[p:s.find('"', p)])
                    break
            for tag in ['GimbalYawDegree="', 'drone-dji:GimbalYawDegree="']:
                if tag in s:
                    p = s.find(tag) + len(tag)
                    gimbal_yaw = float(s[p:s.find('"', p)])
                    break
    except:
        pass
    return rel_alt, gimbal_pitch, gimbal_yaw

cat_df = pd.read_csv('catalogo_fotos_drone_2026.csv')
cat_df['dist_m'] = np.sqrt(
    ((cat_df['lat'] - cx_lat) * 111000)**2 + 
    ((cat_df['lon'] - cx_lon) * 111000 * np.cos(np.radians(cx_lat)))**2
)

# Filter all photos within 80m of complex in 2026
close_df = cat_df[cat_df['dist_m'] <= 80.0].copy()
print(f"Total fotos a <= 80m do complexo em 2026: {len(close_df)}")

# Scan their relative altitudes and pitch
details = []
for idx, r in close_df.iterrows():
    fp = os.path.join(root, r['folder'], r['file'])
    if not os.path.exists(fp): continue
    ra, gp, gy = get_info(fp)
    details.append({
        'folder': r['folder'],
        'file': r['file'],
        'dist_m': round(r['dist_m'], 1),
        'alt_gps': round(r['alt'], 1),
        'rel_alt': round(ra, 1) if ra is not None else None,
        'pitch': round(gp, 1) if gp is not None else None,
        'dt': r['dt']
    })

det_df = pd.DataFrame(details)
print(det_df.describe())

# Find photos with rel_alt <= 50m (or if not present, (alt_gps - 477) <= 50m or alt_gps <= 536m)
# Notice in 111MEDIA: alt_gps is 535.0m. If takeoff was at ~533m or ground is 477m, what is rel_alt?
print("\nFotos em 111MEDIA com menor distancia:")
print(det_df[det_df['folder'] == '111MEDIA'].sort_values('dist_m').head(20).to_string())

print("\nFotos em 109MEDIA com menor distancia:")
print(det_df[det_df['folder'] == '109MEDIA'].sort_values('dist_m').head(20).to_string())

print("\nFotos em 110MEDIA com menor distancia:")
print(det_df[det_df['folder'] == '110MEDIA'].sort_values('dist_m').head(20).to_string())
