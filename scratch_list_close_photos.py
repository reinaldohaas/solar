import pandas as pd
import numpy as np

cx_lat = -27.39587
cx_lon = -49.34734
df = pd.read_csv('catalogo_fotos_drone_2026.csv')
df['dist_m'] = np.sqrt(((df['lat'] - cx_lat) * 111000)**2 + ((df['lon'] - cx_lon) * 111000 * np.cos(np.radians(cx_lat)))**2)

close = df[df['dist_m'] <= 25.0].sort_values(['folder', 'file'])
print(f"Total fotos a <= 25m do complexo: {len(close)}")
print("\nContagem por pasta:")
print(close['folder'].value_counts())

for folder_name in close['folder'].unique():
    sub = close[close['folder'] == folder_name]
    f_first = sub['file'].iloc[0]
    f_last = sub['file'].iloc[-1]
    d_first = sub['dt'].iloc[0]
    d_last = sub['dt'].iloc[-1]
    print(f"  {folder_name}: {len(sub)} fotos ({f_first} a {f_last}) de {d_first} a {d_last}")
