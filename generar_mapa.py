import pandas as pd
import json
import os

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTAwZ4dc9y6iaaz0Q-gzZX5iredCR-ImuFpEWjMByMk_UialzXj5YX5C_jx_iL5CzY6d7VUzRFl3S5y/pub?gid=1451450324&single=true&output=csv"
OUTPUT_FILE = "docs/index.html"

MESES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
         7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
COLOR_MAP = {'Con Muertos':'#E63946','Con Heridos':'#F4A261','Solo Danos':'#2A9D8F','Solo Daños':'#2A9D8F'}

def limpiar_coord(v):
    try: return float(str(v).strip().replace(",","."))
    except: return None

def cargar_datos(url):
    df = pd.read_csv(url)
    lat_col = next((c for c in df.columns if 'latitud' in c.lower()), None)
    lon_col = next((c for c in df.columns if 'longitud' in c.lower()), None)
    df['lat'] = df[lat_col].apply(limpiar_coord)
    df['lon'] = df[lon_col].apply(limpiar_coord)
    df = df.dropna(subset=['lat','lon'])
    df = df[df['lat'].between(-5,15) & df['lon'].between(-82,-65)]
    fecha_col = next((c for c in df.columns if 'fecha' in c.lower()), None)
    if fecha_col:
        df['FechaHecho'] = pd.to_datetime(df[fecha_col], errors='coerce', dayfirst=True)
        df['Anio'] = df['FechaHecho'].dt.year.fillna(0).astype(int)
        df['Mes'] = df['FechaHecho'].dt.month.fillna(0).astype(int)
    muertos_col = next((c for c in df.columns if 'muerto' in c.lower()), None)
    heridos_col = next((c for c in df.columns if 'herido' in c.lower()), None)
    if muertos_col:
        df[muertos_col] = pd.to_numeric(df[muertos_col], errors='coerce').fillna(0).astype(int)
    if heridos_col:
        df[heridos_col] = pd.to_numeric(df[heridos_col], errors='coerce').fillna(0).astype(int)
    return df

def generar_html(df):
    gravedad_col = next((c for c in df.columns if 'gravedad' in c.lower()), None)
    clase_col    = next((c for c in df.columns if 'clase' in c.lower() and 'acc' in c.lower()), None)
    dir_col      = next((c for c in df.columns if 'direcc' in c.lower()), None)
    hora_col     = next((c for c in df.columns if 'hora' in c.lower()), None)
    muertos_col  = next((c for c in df.columns if 'muerto' in c.lower()), None)
    heridos_col  = next((c for c in df.columns if 'herido' in c.lower()), None)
    cod_col      = next((c for c in df.columns if 'codrot' in c.lower() or 'ipat' in c.lower()), None)

    points_data = []
    for _, row in df.iterrows():
        g = str(row[gravedad_col]) if gravedad_col else 'N/D'
        fecha = str(row['FechaHecho'].date()) if 'FechaHecho' in df.columns and pd.notna(row['FechaHecho']) else 'N/D'
        muertos = int(row[muertos_col]) if muertos_col else 0
        heridos = int(row[heridos_col]) if heridos_col else 0
        points_data.append({
            'lat': float(row['lat']), 'lon': float(row['lon']),
            'gravedad': g,
            'color': COLOR_MAP.get(g, '#888888'),
            'codrot': str(row[cod_col]) if cod_col else 'N/D',
            'direccion': str(row[dir_col]) if dir_col else 'N/D',
            'fecha': fecha,
            'hora': str(row[hora_col]) if hora_col else 'N/D',
            'clase': str(row[clase_col]) if clase_col else 'N/D',
            'muertos': muertos,
            'heridos': heridos,
            'anio': int(row.get('Anio', 0)),
            'mes': int(row.get('Mes', 0)),
        })

    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    anios = sorted([a for a in df['Anio'].unique().tolist() if a > 0]) if 'Anio' in df.columns else []
    meses_disp = sorted([m for m in df['Mes'].unique().tolist() if m > 0]) if 'Mes' in df.columns else []
    points_json = json.dumps(points_data, ensure_ascii=False)
    anios_opts = ''.join(f'<option value="{a}">{a}</option>' for a in anios)
    meses_opts = ''.join(f'<option value="{m}">{MESES.get(m,"Mes "+str(m))}</option>' for m in meses_disp)

    html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Siniestros Viales - Aguazul, Casanare</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e}
#map{position:fixed;top:0;left:320px;right:0;bottom:0;z-index:1}
#sidebar{position:fixed;top:0;left:0;width:320px;height:100vh;background:#1e1e2e;color:#e0e0e0;z-index:10;display:flex;flex-direction:column;overflow:hidden;box-shadow:4px 0 20px rgba(0,0,0,0.4)}
#header{background:linear-gradient(135deg,#2d6a4f,#1b4332);padding:16px 20px;flex-shrink:0}
#header h2{font-size:15px;color:#fff;font-weight:700;line-height:1.4}
#header p{font-size:11px;color:#a8d5c2;margin-top:4px}
#scroll-content{flex:1;overflow-y:auto;padding:16px}
#scroll-content::-webkit-scrollbar{width:4px}
#scroll-content::-webkit-scrollbar-thumb{background:#444;border-radius:4px}
.section-title{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#888;margin:16px 0 8px}
.section-title:first-child{margin-top:0}
.filter-group{margin-bottom:10px}
.filter-group label{font-size:12px;color:#aaa;display:block;margin-bottom:4px}
.filter-group select{width:100%;padding:8px 10px;border-radius:8px;border:1px solid #333;background:#2a2a3e;color:#e0e0e0;font-size:13px;cursor:pointer;outline:none;transition:border-color 0.2s}
.filter-group select:hover,.filter-group select:focus{border-color:#2d6a4f}
.gravity-filters{display:flex;flex-direction:column;gap:8px}
.gravity-item{display:flex;align-items:center;gap:10px;background:#2a2a3e;border-radius:8px;padding:8px 12px;cursor:pointer;border:1px solid #333;transition:all 0.2s;user-select:none}
.gravity-item:hover{border-color:#555;background:#303045}
.gravity-dot{width:14px;height:14px;border-radius:50%;background:var(--color);flex-shrink:0;box-shadow:0 0 6px var(--color)}
.gravity-label{font-size:13px;color:#ddd;flex:1}
.gravity-count{font-size:12px;font-weight:700;color:var(--color);background:rgba(255,255,255,0.05);padding:2px 8px;border-radius:20px}
.gravity-item.inactive{opacity:0.35}
.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.stat-card{background:#2a2a3e;border-radius:10px;padding:10px 12px;border:1px solid #333;text-align:center}
.stat-card.full{grid-column:1/-1}
.stat-num{font-size:26px;font-weight:700;color:#fff;line-height:1}
.stat-num.red{color:#E63946}
.stat-num.orange{color:#F4A261}
.stat-num.teal{color:#2A9D8F}
.stat-num.yellow{color:#F9C74F}
.stat-label{font-size:10px;color:#888;margin-top:3px;text-transform:uppercase;letter-spacing:0.5px;line-height:1.2}
.toggle-row{display:flex;gap:8px;margin-bottom:10px}
.toggle-btn{flex:1;padding:8px;border-radius:8px;border:1px solid #333;background:#2a2a3e;color:#ddd;font-size:12px;cursor:pointer;transition:all 0.2s;text-align:center}
.toggle-btn:hover{background:#303045;border-color:#555}
.toggle-btn.on{background:#2d6a4f;border-color:#2d6a4f;color:#fff}
#footer{padding:10px 16px;border-top:1px solid #2a2a3e;font-size:10px;color:#555;text-align:center;flex-shrink:0}
.leaflet-control-attribution{font-size:9px}
</style>
</head>
<body>
<div id="sidebar">
  <div id="header">
    <h2>🚦 Siniestros Viales<br>Aguazul, Casanare</h2>
    <p>Observatorio Territorial de Seguridad Vial</p>
  </div>
  <div id="scroll-content">
    <div class="section-title">🔍 Filtros</div>
    <div class="filter-group">
      <label>Año</label>
      <select id="filtro-anio" onchange="aplicarFiltros()">
        <option value="todos">Todos los años</option>
        ANIOS_OPTS
      </select>
    </div>
    <div class="filter-group">
      <label>Mes</label>
      <select id="filtro-mes" onchange="aplicarFiltros()">
        <option value="todos">Todos los meses</option>
        MESES_OPTS
      </select>
    </div>
    <div class="section-title">⚠ Gravedad del siniestro</div>
    <div class="gravity-filters">
      <div class="gravity-item active" id="g-muertos" style="--color:#E63946" onclick="toggleGravedad('Con Muertos')">
        <div class="gravity-dot"></div>
        <span class="gravity-label">Con Muertos</span>
        <span class="gravity-count" id="cnt-grav-muertos">0</span>
      </div>
      <div class="gravity-item active" id="g-heridos" style="--color:#F4A261" onclick="toggleGravedad('Con Heridos')">
        <div class="gravity-dot"></div>
        <span class="gravity-label">Con Heridos</span>
        <span class="gravity-count" id="cnt-grav-heridos">0</span>
      </div>
      <div class="gravity-item active" id="g-danos" style="--color:#2A9D8F" onclick="toggleGravedad('Solo Daños')">
        <div class="gravity-dot"></div>
        <span class="gravity-label">Solo Daños</span>
        <span class="gravity-count" id="cnt-grav-danos">0</span>
      </div>
    </div>
    <div class="section-title">📊 Resumen de siniestros</div>
    <div class="stats-grid">
      <div class="stat-card full">
        <div class="stat-num" id="s-total">0</div>
        <div class="stat-label">Total Siniestros</div>
      </div>
      <div class="stat-card">
        <div class="stat-num red" id="s-sin-muertos">0</div>
        <div class="stat-label">Siniestros<br>con Muertos</div>
      </div>
      <div class="stat-card">
        <div class="stat-num orange" id="s-sin-heridos">0</div>
        <div class="stat-label">Siniestros<br>con Heridos</div>
      </div>
      <div class="stat-card">
        <div class="stat-num teal" id="s-sin-danos">0</div>
        <div class="stat-label">Siniestros<br>Solo Daños</div>
      </div>
    </div>
    <div class="section-title">🏥 Resumen de víctimas</div>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-num red" id="s-personas-muertas">0</div>
        <div class="stat-label">Personas<br>Fallecidas</div>
      </div>
      <div class="stat-card">
        <div class="stat-num orange" id="s-personas-heridas">0</div>
        <div class="stat-label">Personas<br>Heridas</div>
      </div>
      <div class="stat-card full">
        <div class="stat-num yellow" id="s-total-victimas">0</div>
        <div class="stat-label">Total Víctimas</div>
      </div>
    </div>
    <div class="section-title">🗺 Capas del mapa</div>
    <div class="toggle-row">
      <button class="toggle-btn on" id="btn-calor" onclick="toggleCalor()">🔥 Calor</button>
      <button class="toggle-btn on" id="btn-puntos" onclick="togglePuntos()">📍 Puntos</button>
    </div>
  </div>
  <div id="footer">Actualización automática diaria · ROT Aguazul</div>
</div>
<div id="map"></div>
<script>
const PUNTOS = POINTS_JSON;
const map = L.map('map').setView([CENTER_LAT, CENTER_LON], 14);
const capas = {
  'Calles (OpenStreetMap)': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap'}),
  'Satélite (Esri)': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{attribution:'© Esri'}),
  'Calles detalladas': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',{attribution:'© Esri'})
};
capas['Calles (OpenStreetMap)'].addTo(map);
L.control.layers(capas,{},{position:'topright'}).addTo(map);
let markersLayer=L.layerGroup().addTo(map);
let heatLayer=null,mostrarCalor=true,mostrarPuntos=true;
let gravedadesActivas=new Set(['Con Muertos','Con Heridos','Solo Daños']);
function crearHeat(datos){
  if(heatLayer)map.removeLayer(heatLayer);
  if(!datos.length)return;
  heatLayer=L.heatLayer(datos.map(p=>[p.lat,p.lon,1]),{radius:25,blur:15,maxZoom:16,gradient:{0.2:'yellow',0.5:'orange',0.8:'red',1.0:'darkred'}});
  if(mostrarCalor)heatLayer.addTo(map);
}
function toggleCalor(){
  mostrarCalor=!mostrarCalor;
  const btn=document.getElementById('btn-calor');
  if(mostrarCalor){if(heatLayer)heatLayer.addTo(map);btn.classList.add('on');}
  else{if(heatLayer)map.removeLayer(heatLayer);btn.classList.remove('on');}
}
function togglePuntos(){
  mostrarPuntos=!mostrarPuntos;
  const btn=document.getElementById('btn-puntos');
  if(mostrarPuntos){markersLayer.addTo(map);btn.classList.add('on');}
  else{map.removeLayer(markersLayer);btn.classList.remove('on');}
}
function toggleGravedad(g){
  const ids={'Con Muertos':'g-muertos','Con Heridos':'g-heridos','Solo Daños':'g-danos'};
  const el=document.getElementById(ids[g]);
  if(gravedadesActivas.has(g)){gravedadesActivas.delete(g);el.classList.remove('active');el.classList.add('inactive');}
  else{gravedadesActivas.add(g);el.classList.add('active');el.classList.remove('inactive');}
  aplicarFiltros();
}
function aplicarFiltros(){
  const anio=document.getElementById('filtro-anio').value;
  const mes=document.getElementById('filtro-mes').value;
  const filtrados=PUNTOS.filter(p=>(anio==='todos'||p.anio==anio)&&(mes==='todos'||p.mes==mes)&&gravedadesActivas.has(p.gravedad));
  markersLayer.clearLayers();
  filtrados.forEach(p=>{
    const c=L.circleMarker([p.lat,p.lon],{radius:8,color:'white',weight:1.5,fillColor:p.color,fillOpacity:0.9});
    c.bindPopup(`<div style="font-family:'Segoe UI',Arial;font-size:13px;min-width:230px"><div style="background:${p.color};color:white;padding:8px 12px;margin:-1px -1px 8px;border-radius:4px 4px 0 0"><b>⚠ ${p.gravedad}</b></div><div style="padding:0 4px 4px"><b>Código:</b> ${p.codrot}<br><b>Dirección:</b> ${p.direccion}<br><b>Fecha:</b> ${p.fecha} <b>Hora:</b> ${p.hora}<br><b>Clase:</b> ${p.clase}<br><b>Fallecidos:</b> ${p.muertos}<br><b>Heridos:</b> ${p.heridos}<br><hr style="margin:6px 0"><a href="https://www.google.com/maps?q=${p.lat},${p.lon}" target="_blank" style="color:#1a73e8;font-size:12px">📍 Ver en Google Maps / Street View</a></div></div>`,{maxWidth:280});
    c.bindTooltip(`<b>${p.gravedad}</b><br>${p.direccion}`,{sticky:true});
    c.addTo(markersLayer);
  });
  crearHeat(filtrados);
  const sinMuertos=filtrados.filter(p=>p.gravedad==='Con Muertos').length;
  const sinHeridos=filtrados.filter(p=>p.gravedad==='Con Heridos').length;
  const sinDanos=filtrados.filter(p=>p.gravedad==='Solo Daños').length;
  const persMuertas=filtrados.reduce((s,p)=>s+p.muertos,0);
  const persHeridas=filtrados.reduce((s,p)=>s+p.heridos,0);
  document.getElementById('s-total').textContent=filtrados.length;
  document.getElementById('s-sin-muertos').textContent=sinMuertos;
  document.getElementById('s-sin-heridos').textContent=sinHeridos;
  document.getElementById('s-sin-danos').textContent=sinDanos;
  document.getElementById('s-personas-muertas').textContent=persMuertas;
  document.getElementById('s-personas-heridas').textContent=persHeridas;
  document.getElementById('s-total-victimas').textContent=persMuertas+persHeridas;
  document.getElementById('cnt-grav-muertos').textContent=sinMuertos;
  document.getElementById('cnt-grav-heridos').textContent=sinHeridos;
  document.getElementById('cnt-grav-danos').textContent=sinDanos;
}
aplicarFiltros();
</script>
</body>
</html>"""

    html = html.replace('ANIOS_OPTS', anios_opts)
    html = html.replace('MESES_OPTS', meses_opts)
    html = html.replace('POINTS_JSON', points_json)
    html = html.replace('CENTER_LAT', str(center_lat))
    html = html.replace('CENTER_LON', str(center_lon))
    return html

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    print("Cargando datos desde Google Sheets...")
    df = cargar_datos(SHEET_URL)
    print(f"✓ {len(df)} siniestros cargados")
    html = generar_html(df)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Mapa guardado en {OUTPUT_FILE}")
