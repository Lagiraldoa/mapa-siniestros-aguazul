import pandas as pd
import json
import os

SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTAwZ4dc9y6iaaz0Q-gzZX5iredCR-ImuFpEWjMByMk_UialzXj5YX5C_jx_iL5CzY6d7VUzRFl3S5y/pub?gid=1451450324&single=true&output=csv"
OUTPUT_FILE = "docs/index.html"

MESES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
         7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
COLOR_MAP = {'Con Muertos':'#FF0000','Con Heridos':'#FF8C00','Solo Daños':'#FFD700'}

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
        fecha = str(row['FechaHecho'].date()) if pd.notna(row.get('FechaHecho')) else 'N/D'
        points_data.append({
            'lat': row['lat'], 'lon': row['lon'],
            'gravedad': g,
            'color': COLOR_MAP.get(g, '#888888'),
            'codrot': str(row[cod_col]) if cod_col else 'N/D',
            'direccion': str(row[dir_col]) if dir_col else 'N/D',
            'fecha': fecha,
            'hora': str(row[hora_col]) if hora_col else 'N/D',
            'clase': str(row[clase_col]) if clase_col else 'N/D',
            'muertos': int(row[muertos_col]) if muertos_col and str(row[muertos_col]).lstrip('-').isdigit() else 0,
            'heridos': int(row[heridos_col]) if heridos_col and str(row[heridos_col]).lstrip('-').isdigit() else 0,
            'anio': int(row.get('Anio', 0)),
            'mes': int(row.get('Mes', 0)),
        })

    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    anios = sorted(df['Anio'].unique().tolist()) if 'Anio' in df.columns else []
    meses_disp = sorted(df['Mes'].unique().tolist()) if 'Mes' in df.columns else []
    points_json = json.dumps(points_data, ensure_ascii=False)

    anios_opts = ''.join(f'<option value="{a}">{a}</option>' for a in anios if a > 0)
    meses_opts = ''.join(f'<option value="{m}">{MESES.get(m,"Mes "+str(m))}</option>' for m in meses_disp if m > 0)

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Siniestros Viales - Aguazul</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:Arial,sans-serif}}
        #map{{width:100%;height:100vh}}
        #panel{{position:fixed;top:10px;left:50%;transform:translateX(-50%);z-index:1000;background:white;padding:10px 16px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.2);display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:center}}
        #panel h3{{font-size:14px;color:#333;white-space:nowrap}}
        #panel select{{padding:5px 10px;border-radius:6px;border:1px solid #ccc;font-size:13px;cursor:pointer;background:#f8f8f8}}
        #legend{{position:fixed;bottom:30px;left:15px;z-index:1000;background:white;padding:12px 16px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.2);font-size:13px}}
        .dot{{display:inline-block;width:12px;height:12px;border-radius:50%;margin-right:6px}}
        #stats{{position:fixed;bottom:30px;right:15px;z-index:1000;background:white;padding:12px 16px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,0.2);font-size:13px;min-width:160px}}
        .btn{{padding:5px 12px;border-radius:6px;border:1px solid #ccc;font-size:13px;cursor:pointer;background:#f8f8f8}}
        .btn:hover{{background:#eee}}
    </style>
</head>
<body>
<div id="map"></div>
<div id="panel">
    <h3>🚦 Siniestros Viales — Aguazul, Casanare</h3>
    <select id="filtro-anio" onchange="aplicarFiltros()">
        <option value="todos">📅 Todos los años</option>
        {anios_opts}
    </select>
    <select id="filtro-mes" onchange="aplicarFiltros()">
        <option value="todos">📆 Todos los meses</option>
        {meses_opts}
    </select>
    <button class="btn" onclick="toggleCalor()" id="btn-calor">🔥 Ocultar Calor</button>
</div>
<div id="legend">
    <b>Gravedad</b><br><br>
    <span class="dot" style="background:#FF0000"></span>Con Muertos<br>
    <span class="dot" style="background:#FF8C00;margin-top:4px"></span>Con Heridos<br>
    <span class="dot" style="background:#FFD700;margin-top:4px"></span>Solo Daños<br>
    <hr style="margin:6px 0"><small>📍 Clic = detalles</small>
</div>
<div id="stats">
    <b>📊 Resumen</b>
    <div>Total: <b id="s-total">0</b></div>
    <div>🔴 Muertos: <b id="s-muertos">0</b></div>
    <div>🟠 Heridos: <b id="s-heridos">0</b></div>
    <div>🟡 Solo Daños: <b id="s-danos">0</b></div>
</div>
<script>
const map = L.map('map').setView([{center_lat},{center_lon}],14);
const capas = {{
    'Calles (OpenStreetMap)': L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'OSM'}}),
    'Satélite (Esri)': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}',{{attribution:'Esri'}}),
    'Calles detalladas (Esri)': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}',{{attribution:'Esri'}})
}};
capas['Calles (OpenStreetMap)'].addTo(map);
L.control.layers(capas).addTo(map);
const PUNTOS={points_json};
let markersLayer=L.layerGroup().addTo(map);
let heatLayer=null,mostrarCalor=true;
function crearHeat(datos){{
    if(heatLayer)map.removeLayer(heatLayer);
    heatLayer=L.heatLayer(datos.map(p=>[p.lat,p.lon,1]),{{radius:25,blur:15,maxZoom:16,gradient:{{0.2:'yellow',0.5:'orange',0.8:'red',1.0:'darkred'}}}});
    if(mostrarCalor)heatLayer.addTo(map);
}}
function toggleCalor(){{
    mostrarCalor=!mostrarCalor;
    if(mostrarCalor){{if(heatLayer)heatLayer.addTo(map);document.getElementById('btn-calor').textContent='🔥 Ocultar Calor';}}
    else{{if(heatLayer)map.removeLayer(heatLayer);document.getElementById('btn-calor').textContent='🔥 Mostrar Calor';}}
}}
function aplicarFiltros(){{
    const anio=document.getElementById('filtro-anio').value;
    const mes=document.getElementById('filtro-mes').value;
    const filtrados=PUNTOS.filter(p=>(anio==='todos'||p.anio==anio)&&(mes==='todos'||p.mes==mes));
    markersLayer.clearLayers();
    filtrados.forEach(p=>{{
        const c=L.circleMarker([p.lat,p.lon],{{radius:8,color:'white',weight:1.5,fillColor:p.color,fillOpacity:0.9}});
        c.bindPopup(`<div style="font-family:Arial;font-size:13px;min-width:220px"><b style="color:${{p.color}};font-size:14px">⚠ ${{p.gravedad}}</b><br><hr style="margin:4px 0"><b>Código:</b> ${{p.codrot}}<br><b>Dirección:</b> ${{p.direccion}}<br><b>Fecha:</b> ${{p.fecha}}<br><b>Hora:</b> ${{p.hora}}<br><b>Clase:</b> ${{p.clase}}<br><b>Muertos:</b> ${{p.muertos}}<br><b>Heridos:</b> ${{p.heridos}}<br><hr style="margin:4px 0"><a href="https://www.google.com/maps?q=${{p.lat}},${{p.lon}}" target="_blank" style="color:#1a73e8">📍 Ver en Google Maps</a></div>`,{{maxWidth:270}});
        c.bindTooltip(`${{p.gravedad}} | ${{p.direccion}}`);
        c.addTo(markersLayer);
    }});
    crearHeat(filtrados);
    document.getElementById('s-total').textContent=filtrados.length;
    document.getElementById('s-muertos').textContent=filtrados.filter(p=>p.gravedad==='Con Muertos').length;
    document.getElementById('s-heridos').textContent=filtrados.filter(p=>p.gravedad==='Con Heridos').length;
    document.getElementById('s-danos').textContent=filtrados.filter(p=>p.gravedad==='Solo Daños').length;
}}
aplicarFiltros();
</script>
</body>
</html>"""

if __name__ == "__main__":
    os.makedirs("docs", exist_ok=True)
    print("Cargando datos desde Google Sheets...")
    df = cargar_datos(SHEET_URL)
    print(f"✓ {len(df)} siniestros cargados")
    html = generar_html(df)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ Mapa guardado en {OUTPUT_FILE}")
