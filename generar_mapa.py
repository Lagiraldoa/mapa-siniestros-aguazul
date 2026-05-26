import pandas as pd
import folium
from folium.plugins import HeatMap

# ─── CONFIGURACIÓN ───────────────────────────────────────────────
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTAwZ4dc9y6iaaz0Q-gzZX5iredCR-ImuFpEWjMByMk_UialzXj5YX5C_jx_iL5CzY6d7VUzRFl3S5y/pub?gid=1451450324&single=true&output=csv"
OUTPUT_FILE = "docs/index.html"
# ─────────────────────────────────────────────────────────────────

def limpiar_coordenada(valor):
    """Limpia y convierte coordenadas a float."""
    try:
        return float(str(valor).strip().replace(",", "."))
    except:
        return None

def cargar_datos(url):
    df = pd.read_csv(url)
    # Detectar columnas de coordenadas
    lat_col = next((c for c in df.columns if 'latitud' in c.lower()), None)
    lon_col = next((c for c in df.columns if 'longitud' in c.lower()), None)
    if not lat_col or not lon_col:
        raise ValueError(f"No se encontraron columnas de coordenadas. Columnas: {list(df.columns)}")
    df['lat'] = df[lat_col].apply(limpiar_coordenada)
    df['lon'] = df[lon_col].apply(limpiar_coordenada)
    df = df.dropna(subset=['lat', 'lon'])
    df = df[df['lat'].between(-5, 15) & df['lon'].between(-82, -65)]
    return df

def generar_mapa(df):
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()

    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles=None)

    # Mapas base
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='OpenStreetMap', name='Calles (OpenStreetMap)', show=True
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satélite (Esri)', show=False
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Calles detalladas (Esri)', show=False
    ).add_to(m)

    # Mapa de calor
    heat_data = df[['lat', 'lon']].values.tolist()
    HeatMap(
        heat_data, name='🔥 Mapa de Calor',
        radius=25, blur=15, max_zoom=16,
        gradient={0.2: 'yellow', 0.5: 'orange', 0.8: 'red', 1.0: 'darkred'},
        show=True
    ).add_to(m)

    # Colores por gravedad
    config_gravedad = [
        ('Con Muertos',  '#FF0000', '🔴 Con Muertos'),
        ('Con Heridos',  '#FF8C00', '🟠 Con Heridos'),
        ('Solo Daños',   '#FFD700', '🟡 Solo Daños'),
    ]

    gravedad_col = next((c for c in df.columns if 'gravedad' in c.lower()), None)
    clase_col    = next((c for c in df.columns if 'clase' in c.lower() and 'acc' in c.lower()), None)
    dir_col      = next((c for c in df.columns if 'direcc' in c.lower()), None)
    fecha_col    = next((c for c in df.columns if 'fecha' in c.lower()), None)
    hora_col     = next((c for c in df.columns if 'hora' in c.lower()), None)
    muertos_col  = next((c for c in df.columns if 'muerto' in c.lower()), None)
    heridos_col  = next((c for c in df.columns if 'herido' in c.lower()), None)
    cod_col      = next((c for c in df.columns if 'codrot' in c.lower() or 'ipat' in c.lower()), None)

    for gravedad, color, label in config_gravedad:
        layer = folium.FeatureGroup(name=label, show=True)
        if gravedad_col:
            subset = df[df[gravedad_col].astype(str).str.strip() == gravedad]
        else:
            subset = df

        for _, row in subset.iterrows():
            direccion = str(row[dir_col])   if dir_col   else 'N/D'
            fecha     = str(row[fecha_col]) if fecha_col else 'N/D'
            hora      = str(row[hora_col])  if hora_col  else 'N/D'
            clase     = str(row[clase_col]) if clase_col else 'N/D'
            muertos   = str(row[muertos_col]) if muertos_col else '0'
            heridos   = str(row[heridos_col]) if heridos_col else '0'
            cod       = str(row[cod_col])   if cod_col   else 'N/D'

            popup_html = f"""
            <div style="font-family:Arial;font-size:13px;min-width:220px">
                <b style="color:{color};font-size:14px">⚠ {gravedad}</b><br>
                <hr style="margin:4px 0">
                <b>Código:</b> {cod}<br>
                <b>Dirección:</b> {direccion}<br>
                <b>Fecha:</b> {fecha}<br>
                <b>Hora:</b> {hora}<br>
                <b>Clase:</b> {clase}<br>
                <b>Muertos:</b> {muertos}<br>
                <b>Heridos:</b> {heridos}<br>
                <hr style="margin:4px 0">
                <a href="https://www.google.com/maps?q={row['lat']},{row['lon']}"
                   target="_blank" style="color:#1a73e8">
                   📍 Ver en Google Maps / Street View
                </a>
            </div>
            """
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=7,
                color='white', weight=1.5,
                fill=True, fill_color=color, fill_opacity=0.9,
                popup=folium.Popup(popup_html, max_width=270),
                tooltip=f"{gravedad} | {direccion}"
            ).add_to(layer)

        layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    # Leyenda
    total = len(df)
    con_muertos = len(df[df[gravedad_col].astype(str).str.strip() == 'Con Muertos']) if gravedad_col else '-'
    con_heridos = len(df[df[gravedad_col].astype(str).str.strip() == 'Con Heridos']) if gravedad_col else '-'
    solo_danos  = len(df[df[gravedad_col].astype(str).str.strip() == 'Solo Daños'])  if gravedad_col else '-'

    legend_html = f"""
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;
                background:white;padding:14px 18px;border-radius:10px;
                box-shadow:2px 2px 10px rgba(0,0,0,0.25);font-family:Arial;font-size:13px">
        <b style="font-size:14px">Gravedad del Siniestro</b><br><br>
        <span style="background:#FF0000;border-radius:50%;display:inline-block;
                     width:12px;height:12px;margin-right:6px"></span>
        Con Muertos &nbsp;<b>({con_muertos})</b><br>
        <span style="background:#FF8C00;border-radius:50%;display:inline-block;
                     width:12px;height:12px;margin-right:6px;margin-top:5px"></span>
        Con Heridos &nbsp;<b>({con_heridos})</b><br>
        <span style="background:#FFD700;border-radius:50%;display:inline-block;
                     width:12px;height:12px;margin-right:6px;margin-top:5px"></span>
        Solo Daños &nbsp;<b>({solo_danos})</b><br>
        <hr style="margin:8px 0">
        <b>Total: {total} siniestros</b><br>
        <small style="color:gray">📍 Clic en punto = detalles</small>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Título
    title_html = """
    <div style="position:fixed;top:10px;left:50%;transform:translateX(-50%);
                z-index:1000;background:white;padding:8px 20px;border-radius:8px;
                box-shadow:2px 2px 8px rgba(0,0,0,0.2);font-family:Arial">
        <b style="font-size:15px">🚦 Siniestros Viales — Aguazul, Casanare</b>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m

if __name__ == "__main__":
    import os
    os.makedirs("docs", exist_ok=True)
    print("Cargando datos desde Google Sheets...")
    df = cargar_datos(SHEET_URL)
    print(f"✓ {len(df)} siniestros cargados")
    print("Generando mapa...")
    mapa = generar_mapa(df)
    mapa.save(OUTPUT_FILE)
    print(f"✓ Mapa guardado en {OUTPUT_FILE}")
