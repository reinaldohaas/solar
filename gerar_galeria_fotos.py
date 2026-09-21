import os
import json
import pandas as pd
from PIL import Image

SOLAR_DIR = r"C:\Users\haas\github\solar"
TARGET_DIR = os.path.join(SOLAR_DIR, "fotos_drone_local_projeto")
OVERHEAD_DIR = os.path.join(TARGET_DIR, "direto_em_cima_do_complexo")
THUMBS_DIR = os.path.join(TARGET_DIR, "thumbs")
os.makedirs(THUMBS_DIR, exist_ok=True)

CSV_PATH = os.path.join(TARGET_DIR, "catalogo_fotos_direto_em_cima.csv")
df = pd.read_csv(CSV_PATH)

print(f"Gerando miniaturas para {len(df)} fotos...")
thumb_count = 0

for idx, row in df.iterrows():
    fname = row['filename']
    img_path = os.path.join(OVERHEAD_DIR, fname)
    thumb_path = os.path.join(THUMBS_DIR, fname)
    
    if not os.path.exists(thumb_path) and os.path.exists(img_path):
        try:
            with Image.open(img_path) as im:
                im.thumbnail((480, 360), Image.BILINEAR)
                im.save(thumb_path, format="JPEG", quality=75)
                thumb_count += 1
        except Exception as e:
            print(f"Erro em {fname}: {e}")

print(f"Miniaturas geradas: {thumb_count} (Total na pasta: {len(os.listdir(THUMBS_DIR))})")

# HTML Gallery Generation
html_content = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Galeria de Fotos do Drone - Voo 2026 sobre o Complexo</title>
<style>
  :root {
    --bg-main: #0d1117;
    --bg-card: #161b22;
    --border: #30363d;
    --accent: #58a6ff;
    --accent-gold: #f1c40f;
    --text-primary: #c9d1d9;
    --text-bright: #ffffff;
    --badge-bg: #21262d;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-main);
    color: var(--text-primary);
    padding: 20px;
  }
  header {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .header-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
  }
  h1 { font-size: 22px; color: var(--text-bright); display: flex; align-items: center; gap: 10px; }
  .subtitle { font-size: 14px; color: #8b949e; }
  .stats-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
  }
  .stat-pill {
    background: var(--badge-bg);
    border: 1px solid var(--border);
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 500;
  }
  .stat-pill b { color: var(--accent); }
  .controls-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    align-items: center;
  }
  .btn-filter {
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 8px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    transition: all 0.2s;
  }
  .btn-filter:hover, .btn-filter.active {
    background: var(--accent);
    color: #000000;
    border-color: var(--accent);
  }
  .search-input {
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: #fff;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    min-width: 220px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
  }
  .card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.2s, border-color 0.2s;
    display: flex;
    flex-direction: column;
  }
  .card:hover {
    transform: translateY(-3px);
    border-color: var(--accent);
  }
  .card-img {
    width: 100%;
    aspect-ratio: 4/3;
    object-fit: cover;
    background: #000;
    display: block;
  }
  .card-info {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 12px;
  }
  .card-name {
    font-size: 13px;
    font-weight: bold;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .card-meta {
    display: flex;
    justify-content: space-between;
    color: #8b949e;
  }
  .card-meta b { color: #58a6ff; }
  .badge-dist {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: bold;
    background: rgba(88, 166, 255, 0.15);
    color: #58a6ff;
  }
  .badge-dist.ultra { background: rgba(46, 204, 113, 0.2); color: #2ecc71; border: 1px solid #2ecc71; }

  /* Lightbox */
  .modal {
    display: none;
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    background: rgba(0, 0, 0, 0.92);
    z-index: 9999;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    backdrop-filter: blur(5px);
  }
  .modal.open { display: flex; }
  .modal-header {
    position: absolute;
    top: 15px; left: 20px; right: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #fff;
  }
  .modal-close {
    background: #e74c3c;
    border: none;
    color: #fff;
    font-size: 20px;
    width: 36px; height: 36px;
    border-radius: 50%;
    cursor: pointer;
    font-weight: bold;
  }
  .modal-img-container {
    max-width: 90vw;
    max-height: 80vh;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .modal-img {
    max-width: 100%;
    max-height: 80vh;
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.8);
    object-fit: contain;
  }
  .modal-nav {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: #fff;
    font-size: 28px;
    width: 48px; height: 48px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    justify-content: center;
    align-items: center;
    transition: background 0.2s;
  }
  .modal-nav:hover { background: rgba(88, 166, 255, 0.6); }
  .modal-prev { left: 20px; }
  .modal-next { right: 20px; }
  .modal-footer {
    position: absolute;
    bottom: 15px;
    background: rgba(22, 27, 34, 0.85);
    border: 1px solid var(--border);
    padding: 10px 20px;
    border-radius: 30px;
    display: flex;
    gap: 20px;
    font-size: 13px;
    align-items: center;
  }
  .btn-action {
    background: #238636;
    color: #fff;
    text-decoration: none;
    padding: 6px 14px;
    border-radius: 6px;
    font-weight: bold;
    font-size: 12px;
  }
</style>
</head>
<body>

<header>
  <div class="header-title">
    <div>
      <h1>🚁 Fotos do Drone - Voo 01/03/2026 Diretamente Sobre a Obra</h1>
      <div class="subtitle">Todas as fotografias capturadas em raio ≤ 25m do Salão 12x8m e Campo de Areia 22x12m</div>
    </div>
    <div style="display: flex; gap: 10px;">
      <a href="../visualizador_campo_salao.html" class="btn-action" style="background:#1f6feb;">🗺️ Voltar ao 3D do Complexo</a>
      <a href="../visualizador_3d_sitio.html" class="btn-action" style="background:#238636;">🌍 Visualizador 3D Geral</a>
    </div>
  </div>

  <div class="stats-bar">
    <div class="stat-pill">Total em Cima do Local: <b id="stat-total">315 fotos</b></div>
    <div class="stat-pill">Mais Próxima: <b>2.50 metros</b></div>
    <div class="stat-pill">Data do Voo: <b>01/03/2026 (Recente)</b></div>
    <div class="stat-pill">Altitude de Voo: <b>2.4m a 30m</b></div>
    <div class="stat-pill">Pasta Local: <code>fotos_drone_local_projeto/direto_em_cima_do_complexo</code></div>
  </div>

  <div class="controls-bar">
    <button class="btn-filter active" onclick="setFilter('all')">Todas (315)</button>
    <button class="btn-filter" onclick="setFilter('ultra')">Ultra Próximas (≤ 5m)</button>
    <button class="btn-filter" onclick="setFilter('near')">Perto (≤ 10m)</button>
    <button class="btn-filter" onclick="setFilter('mid')">Até 15m</button>
    <button class="btn-filter" onclick="setFilter('lowalt')">Voos Baixos (Alt ≤ 10m)</button>
    <button class="btn-filter" onclick="setFilter('109')">Série 109MEDIA</button>
    <button class="btn-filter" onclick="setFilter('110')">Série 110MEDIA</button>
    <button class="btn-filter" onclick="setFilter('111')">Série 111MEDIA</button>
    <input type="text" class="search-input" id="search" placeholder="Buscar arquivo (ex: 0963)..." oninput="applyFilters()">
  </div>
</header>

<div class="grid" id="photo-grid"></div>

<!-- Lightbox Modal -->
<div class="modal" id="modal" onclick="closeModal(event)">
  <div class="modal-header">
    <div id="modal-title" style="font-weight: bold; font-size: 16px;"></div>
    <button class="modal-close" onclick="closeModalDirect()">×</button>
  </div>
  <button class="modal-nav modal-prev" onclick="prevPhoto(event)">‹</button>
  <div class="modal-img-container">
    <img id="modal-img" class="modal-img" src="" alt="">
  </div>
  <button class="modal-nav modal-next" onclick="nextPhoto(event)">›</button>
  <div class="modal-footer" id="modal-footer"></div>
</div>

<script>
const photos = JSON_PHOTOS_PLACEHOLDER;
let currentFilter = 'all';
let filteredList = [...photos];
let currentIndex = 0;

function renderGrid() {
  const grid = document.getElementById('photo-grid');
  grid.innerHTML = '';
  filteredList.forEach((p, idx) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openModal(idx);
    
    const isUltra = p.min_dist_m <= 5.0;
    const badgeCls = isUltra ? 'badge-dist ultra' : 'badge-dist';

    card.innerHTML = `
      <img class="card-img" src="thumbs/${p.filename}" loading="lazy" alt="${p.filename}">
      <div class="card-info">
        <div class="card-name">${p.filename}</div>
        <div class="card-meta">
          <span>Distância: <b class="${badgeCls}">${p.min_dist_m}m</b></span>
          <span>Alt: <b>${p.dji_rel_alt_m}m</b></span>
        </div>
        <div class="card-meta">
          <span>Câmera: <b>${p.gimbal_pitch_deg !== null ? p.gimbal_pitch_deg + '°' : 'N/A'}</b></span>
          <span>${p.datetime.split(' ')[1]}</span>
        </div>
      </div>
    `;
    grid.appendChild(card);
  });
  document.getElementById('stat-total').innerText = filteredList.length + ' fotos exibidas';
}

function setFilter(f) {
  currentFilter = f;
  document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  applyFilters();
}

function applyFilters() {
  const term = document.getElementById('search').value.toLowerCase();
  filteredList = photos.filter(p => {
    // text search
    if (term && !p.filename.toLowerCase().includes(term)) return false;
    
    if (currentFilter === 'all') return true;
    if (currentFilter === 'ultra') return p.min_dist_m <= 5.0;
    if (currentFilter === 'near') return p.min_dist_m <= 10.0;
    if (currentFilter === 'mid') return p.min_dist_m <= 15.0;
    if (currentFilter === 'lowalt') return p.dji_rel_alt_m <= 10.0;
    if (currentFilter === '109') return p.original_folder === '109MEDIA';
    if (currentFilter === '110') return p.original_folder === '110MEDIA';
    if (currentFilter === '111') return p.original_folder === '111MEDIA';
    return true;
  });
  renderGrid();
}

function openModal(idx) {
  currentIndex = idx;
  updateModal();
  document.getElementById('modal').classList.add('open');
}

function closeModal(e) {
  if (e.target.id === 'modal' || e.target.classList.contains('modal-img-container')) {
    document.getElementById('modal').classList.remove('open');
  }
}

function closeModalDirect() {
  document.getElementById('modal').classList.remove('open');
}

function prevPhoto(e) {
  if (e) e.stopPropagation();
  if (currentIndex > 0) currentIndex--;
  else currentIndex = filteredList.length - 1;
  updateModal();
}

function nextPhoto(e) {
  if (e) e.stopPropagation();
  if (currentIndex < filteredList.length - 1) currentIndex++;
  else currentIndex = 0;
  updateModal();
}

function updateModal() {
  const p = filteredList[currentIndex];
  document.getElementById('modal-title').innerText = `${p.filename} (${currentIndex + 1} de ${filteredList.length})`;
  document.getElementById('modal-img').src = 'direto_em_cima_do_complexo/' + p.filename;
  
  document.getElementById('modal-footer').innerHTML = `
    <span>Distância ao Salão: <b>${p.dist_salao_m}m</b></span>
    <span>Distância ao Campo: <b>${p.dist_campo_m}m</b></span>
    <span>Altura Relativa: <b>${p.dji_rel_alt_m}m</b></span>
    <span>Pitch Câmera: <b>${p.gimbal_pitch_deg}°</b></span>
    <span>Horário: <b>${p.datetime}</b></span>
    <a href="direto_em_cima_do_complexo/${p.filename}" target="_blank" class="btn-action">Abrir Original 48MP ↗</a>
  `;
}

window.addEventListener('keydown', (e) => {
  if (!document.getElementById('modal').classList.contains('open')) return;
  if (e.key === 'ArrowLeft') prevPhoto();
  if (e.key === 'ArrowRight') nextPhoto();
  if (e.key === 'Escape') closeModalDirect();
});

renderGrid();
</script>
</body>
</html>
"""

json_data = df.to_json(orient='records')
full_html = html_content.replace('JSON_PHOTOS_PLACEHOLDER', json_data)

gallery_path = os.path.join(TARGET_DIR, "galeria_fotos_drone.html")
with open(gallery_path, 'w', encoding='utf-8') as f:
    f.write(full_html)

# Also create a copy or symlink in root solar directory
root_gallery_path = os.path.join(SOLAR_DIR, "galeria_fotos_drone.html")
root_html = full_html.replace('thumbs/', 'fotos_drone_local_projeto/thumbs/').replace('direto_em_cima_do_complexo/', 'fotos_drone_local_projeto/direto_em_cima_do_complexo/')
with open(root_gallery_path, 'w', encoding='utf-8') as f:
    f.write(root_html)

print("Galeria HTML criada com sucesso em:")
print(f"1. {gallery_path}")
print(f"2. {root_gallery_path}")
