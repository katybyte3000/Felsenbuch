import streamlit as st
import pandas as pd
import folium  # für die interaktive Karte
from streamlit_folium import st_folium
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import math

# Lade Umgebungsvariablen
load_dotenv()

# Supabase-Verbindung herstellen
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Überprüfe, ob die Supabase-Variablen geladen wurden
if not url or not key:
    st.error("Fehler: SUPABASE_URL oder SUPABASE_KEY wurden nicht gefunden. Stellen Sie sicher, dass Ihre .env-Datei korrekt ist.")
    st.stop() # Stoppt die Ausführung der App, wenn die Variablen fehlen

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Fehler beim Erstellen des Supabase-Clients: {e}")
    st.stop()

# Daten holen
@st.cache_data
def fetch_data():
    try:
        peaks_df = pd.DataFrame(supabase.table("peaks").select("*").execute().data)
        routes_df = pd.DataFrame(supabase.table("routes").select("*").execute().data)
        ascents_df = pd.DataFrame(supabase.table("ascents").select("*").execute().data)
        
        # Debugging: Prüfen, ob 'done' in ascents_df ist
        if 'done' not in ascents_df.columns:
            st.warning("Debugging: Spalte 'done' NICHT in der 'ascents'-Tabelle gefunden nach dem Abruf von Supabase. Bitte in Supabase überprüfen!")
            # Optional: Füge eine Dummy-Spalte hinzu, um den Code lauffähig zu halten, aber mit Hinweis
            ascents_df['done'] = False # Default-Wert, wenn Spalte fehlt
            
        return peaks_df, routes_df, ascents_df
    except Exception as e:
        st.error(f"Fehler beim Laden der Daten von Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame() # Leere DataFrames zurückgeben

# Mapping der Schwierigkeit
difficulty_mapping = {1: "Leicht", 2: "Ok", 3: "Schwer"}

# Hilfsfunktion: Dreieck-Koordinaten berechnen
def make_triangle(lat, lon, size=0.001):
    """
    Erzeuge 3 Koordinaten für ein gleichseitiges Dreieck
    Größe ca. 0.001 Grad = ~100 m
    """
    if pd.isna(lat) or pd.isna(lon) or pd.isna(size) or size <= 0:
        return None # Gibt None zurück, wenn Eingaben NaN sind oder die Größe ungültig ist

    try:
        return [
            [lat + size, lon],  # Spitze nach oben
            [lat - size / 2, lon - size * math.sqrt(3)/2],
            [lat - size / 2, lon + size * math.sqrt(3)/2],
        ]
    except TypeError: # Fängt Fehler ab, wenn lat/lon/size keine Zahlen sind
        st.error(f"Fehler bei make_triangle: lat={lat}, lon={lon}, size={size} sind keine gültigen Zahlen.")
        return None

# Hauptfunktionen der App
def app():
    st.set_page_config(layout="wide") # Optional: Nutzt die gesamte Bildschirmbreite
    st.title("Gipfelbuch - Kletter-App")

    # 1. Daten holen
    peaks_df, routes_df, ascents_df = fetch_data()

    if peaks_df.empty or routes_df.empty or ascents_df.empty:
        st.warning("Keine Daten verfügbar oder Fehler beim Laden der Daten. Bitte prüfen Sie Ihre Supabase-Verbindung und Tabellen.")
        st.stop() # Stoppt die App, wenn keine Daten geladen werden konnten

    # 🔹 Verknüpfung der ascents und peaks Tabelle
    # Sicherstellen, dass die Spalten für den Merge existieren
    if "route_id" in ascents_df.columns and "route_id" in routes_df.columns:
        ascents_with_route = ascents_df.merge(routes_df, on="route_id", how="left")
    else:
        st.error("Fehlende 'route_id' Spalte in ascents_df oder routes_df.")
        st.stop()
    
    if "peak_id" in ascents_with_route.columns and "peak_id" in peaks_df.columns:
        ascents_with_peak = ascents_with_route.merge(
            peaks_df[['peak_id', 'gipfel', 'gebiet', 'hoehe', 'lat', 'lon']], # Nur benötigte Spalten aus peaks_df
            on="peak_id",
            how="left"
        )
        
        # Sicherstellen, dass 'done' in ascents_with_peak vorhanden ist
        if 'done' not in ascents_with_peak.columns and 'done' in ascents_df.columns:
            if 'ascent_id' in ascents_with_peak.columns:
                ascents_with_peak = ascents_with_peak.merge(
                    ascents_df[['ascent_id', 'done']],
                    on='ascent_id',
                    how='left',
                    suffixes=('', '_from_ascents') 
                )
                if 'done_from_ascents' in ascents_with_peak.columns:
                    # Konfliktbehandlung falls 'done' schon von routes_df kam
                    ascents_with_peak['done'] = ascents_with_peak['done_from_ascents'].fillna(ascents_with_peak['done'])
                    ascents_with_peak.drop(columns=['done_from_ascents'], inplace=True)
            else:
                st.warning("Spalte 'ascent_id' fehlt in 'ascents_with_peak', kann 'done' nicht nachmergen.")
        
        if 'done' not in ascents_with_peak.columns:
            st.warning("Spalte 'done' ist auch nach Merges nicht in 'ascents_with_peak' vorhanden. Füge Dummy-Spalte hinzu.")
            ascents_with_peak['done'] = False # Füllt fehlende Werte mit False


    else:
        st.error("Fehlende 'peak_id' Spalte in der verknüpften Tabelle oder peaks_df.")
        st.stop()

    # 🔹 Berechnung der Anzahl der Routen pro Peak
    route_counts = routes_df.groupby("peak_id").size().reset_index(name="anzahl_routen")
    peaks_df = peaks_df.merge(route_counts, on="peak_id", how="left")
    peaks_df["anzahl_routen"] = peaks_df["anzahl_routen"].fillna(0).astype(int)

    # Sicherstellen, dass ascents_with_peak die 'anzahl_routen' Spalte bekommt
    if 'anzahl_routen' not in ascents_with_peak.columns:
        ascents_with_peak = ascents_with_peak.merge(peaks_df[['peak_id', 'anzahl_routen']], on='peak_id', how='left')
        ascents_with_peak['anzahl_routen'] = ascents_with_peak['anzahl_routen'].fillna(0).astype(int)


    # 2. Filteroptionen
    st.sidebar.title("Filteroptionen")

    # Gebirgspunkt-Filter
    gebiet_filter_options = sorted(peaks_df['gebiet'].unique().tolist()) # Sortieren für bessere Anzeige
    if len(gebiet_filter_options) > 0:
        gebiet_filter = st.sidebar.selectbox('Wähle ein Gebiet', options=['Alle Gebiete'] + gebiet_filter_options)
    else:
        st.sidebar.warning("Keine Gebiete zum Filtern verfügbar.")
        gebiet_filter = 'Alle Gebiete' # Standardwert, wenn keine Optionen

    # Schwierigkeit-Filter (Mapping auf die Textdarstellung)
    # Hinzufügen der "Alle Bewertungen" Option
    schwierigkeit_filter = st.sidebar.selectbox(
        'Wähle die Schwierigkeit', 
        options=["Alle Bewertungen", "Leicht", "Ok", "Schwer"]
    )

    # Umwandeln der Schwierigkeit in numerische Werte (für den Filter)
    difficulty_filter_value = None # Standardmäßig kein Filter
    if schwierigkeit_filter != "Alle Bewertungen":
        difficulty_filter_value = {
            "Leicht": 1,
            "Ok": 2,
            "Schwer": 3
        }[schwierigkeit_filter]

    # Sternchen-Filter (1=hat Stern, 0=hat keinen Stern)
    sternchen_filter = st.sidebar.radio(
        "Wähle die Routen mit oder ohne Sternchen",
        options=["Alle", "Hat Stern", "Hat keinen Stern"]
    )

    # Umwandeln des Sternchenfilters in 1 oder 0
    if sternchen_filter == "Hat Stern":
        sternchen_filter_value = 1
    elif sternchen_filter == "Hat keinen Stern":
        sternchen_filter_value = 0
    else:
        sternchen_filter_value = None  # Zeige alle Routen, unabhängig von Sternchen

    # Höhe-Filter
    if 'hoehe' in peaks_df.columns and pd.api.types.is_numeric_dtype(peaks_df['hoehe']):
        min_hoehe = int(peaks_df['hoehe'].min()) if not peaks_df['hoehe'].empty and pd.notna(peaks_df['hoehe'].min()) else 0
        max_hoehe = int(peaks_df['hoehe'].max()) if not peaks_df['hoehe'].empty and pd.notna(peaks_df['hoehe'].max()) else 3000
        # Setze den Startwert des Sliders auf den Maximalwert, um standardmäßig alle Höhen einzuschließen
        hoehe_filter = st.sidebar.slider('Wähle die maximale Felsenhöhe in Metern', min_value=min_hoehe, max_value=max_hoehe, step=10, value=max_hoehe)
    else:
        st.sidebar.warning("Höhenfilter nicht verfügbar, da 'hoehe' Spalte fehlt oder nicht numerisch ist.")
        hoehe_filter = None

    # Schon gemacht-Filter
    if 'done' in ascents_with_peak.columns: # Prüfe, ob 'done' in der ascents_with_peak DataFrame ist
        gemacht_filter = st.sidebar.checkbox('Schon gemacht')
    else:
        st.sidebar.warning("Option 'Schon gemacht' nicht verfügbar (Spalte 'done' fehlt in Daten).")
        gemacht_filter = False


    # 3. Filter anwenden
    filtered_peaks = ascents_with_peak.copy()

    if gebiet_filter != 'Alle Gebiete': 
        filtered_peaks = filtered_peaks[filtered_peaks['gebiet'] == gebiet_filter]
    
    # NEUE FILTERLOGIK für Schwierigkeit
    if difficulty_filter_value is not None: # Nur filtern, wenn nicht "Alle Bewertungen" gewählt ist
        if 'bewertung' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['bewertung'] == difficulty_filter_value]
        else:
            st.warning("Spalte 'bewertung' nicht gefunden, Schwierigkeitsfilter wird ignoriert.")

    if sternchen_filter_value is not None and 'stern' in filtered_peaks.columns:
        filtered_peaks = filtered_peaks[filtered_peaks['stern'] == sternchen_filter_value]
    elif sternchen_filter_value is not None: 
        st.warning("Spalte 'stern' nicht gefunden, Sternchen-Filter wird ignoriert.")

    if gemacht_filter and 'done' in filtered_peaks.columns:
        filtered_peaks = filtered_peaks[filtered_peaks['done'] == True]
    elif gemacht_filter: 
        st.warning("Spalte 'done' nicht gefunden, 'Schon gemacht'-Filter wird ignoriert.")
    
    if hoehe_filter is not None and 'hoehe' in filtered_peaks.columns:
        # Sicherstellen, dass 'hoehe' numerisch ist, bevor der Filter angewendet wird
        filtered_peaks = filtered_peaks[pd.to_numeric(filtered_peaks['hoehe'], errors='coerce').fillna(0) <= hoehe_filter]


    # **Überprüfung und Bereinigung von NaN-Werten für Kartenplotting**
    initial_rows = len(filtered_peaks)
    
    cols_for_map = ['lat', 'lon', 'hoehe', 'gipfel', 'gebiet', 'anzahl_routen']
    existing_cols_for_map = [col for col in cols_for_map if col in filtered_peaks.columns]
    
    if existing_cols_for_map:
        filtered_peaks = filtered_peaks.dropna(subset=existing_cols_for_map)
        if len(filtered_peaks) < initial_rows:
            st.warning(f"Es wurden {initial_rows - len(filtered_peaks)} Gipfel mit fehlenden Daten (Koordinaten, Höhe etc.) für die Kartenanzeige entfernt.")
    else:
        st.warning("Wichtige Spalten (lat, lon, hoehe) für die Kartenanzeige fehlen in 'filtered_peaks'.")
        filtered_peaks = pd.DataFrame() 

    # 5. Ausgabe der gefilterten Gebirgspunkte als Liste
    st.subheader("Gefilterte Gebirgspunkte")
    if not filtered_peaks.empty:
        display_columns = ['gipfel', 'gebiet', 'hoehe', 'anzahl_routen', 'bewertung', 'stern', 'done']
        actual_display_columns = [col for col in display_columns if col in filtered_peaks.columns]
        
        st.dataframe(filtered_peaks[actual_display_columns])
        st.write(f"Gesamtanzahl der angezeigten Gipfel nach Filtern und Bereinigung: {len(filtered_peaks)}")
    else:
        st.info("Keine Gipfel gefunden, die den aktuellen Filtern entsprechen oder alle notwendigen Daten für die Anzeige haben.")


    # 6. Kartenmittelpunkt berechnen
    st.subheader("Interaktive Karte")
    if not filtered_peaks.empty:
        lat_center = filtered_peaks["lat"].mean()
        lon_center = filtered_peaks["lon"].mean()
    else:
        st.info("Keine Gipfel vorhanden, um die Karte zu zentrieren und Dreiecke anzuzeigen.")
        return 

    # 7. Folium-Karte erstellen
    m = folium.Map(location=[lat_center, lon_center], zoom_start=11)

    # 8. Dreiecke als Polygone einfügen (Größe nach Höhe)
    drawn_triangles_count = 0
    for index, row in filtered_peaks.iterrows():
        required_cols_for_plot = ['lat', 'lon', 'hoehe', 'anzahl_routen', 'gipfel', 'gebiet']
        
        if not all(col in row.index and pd.notna(row[col]) for col in required_cols_for_plot):
            continue 

        hoehe_val = pd.to_numeric(row["hoehe"], errors='coerce')
        if pd.isna(hoehe_val) or hoehe_val < 0: 
            continue

        größe = 0.0012 + (hoehe_val * 0.00011)
        if größe <= 0: 
            continue

        coords = make_triangle(row["lat"], row["lon"], größe)
        if coords: 
            tooltip_text = f"""
            <b>{row['gipfel']}</b><br>
            Höhe: {int(hoehe_val)} m<br>
            Routen: {int(row['anzahl_routen'])}<br>
            Gebiet: {row['gebiet']}
            """
            folium.Polygon(
                locations=coords,
                color=None, 
                fill=True,
                fill_color="black",
                fill_opacity=0.89,
                tooltip=folium.Tooltip(tooltip_text, sticky=True)
            ).add_to(m)
            drawn_triangles_count += 1
        
    st.info(f"Anzahl der auf der Karte gezeichneten Dreiecke: {drawn_triangles_count}")

    # 9. Karte anzeigen
    st_data = st_folium(m, width=1400, height=600)

if __name__ == "__main__":
    app()