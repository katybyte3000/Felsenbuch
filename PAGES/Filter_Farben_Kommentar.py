import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
import os
from dotenv import load_dotenv
import math

# Lade Umgebungsvariablen
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    st.error("Fehler: SUPABASE_URL oder SUPABASE_KEY wurden nicht gefunden. Stellen Sie sicher, dass Ihre .env-Datei korrekt ist.")
    st.stop()

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error(f"Fehler beim Erstellen des Supabase-Clients: {e}")
    st.stop()

@st.cache_data
def fetch_data():
    try:
        peaks_df = pd.DataFrame(supabase.table("peaks").select("*").execute().data)
        routes_df = pd.DataFrame(supabase.table("routes").select("*").execute().data)
        # NEU: Auch 'kommentar' aus ascents_df abrufen
        ascents_df = pd.DataFrame(supabase.table("ascents").select("*, kommentar").execute().data) 

        st.info(f"DEBUG FETCH_DATA: Initial peaks_df rows: {len(peaks_df)}")

        # --- Handling für 'bewertung' in ascents_df ---
        if 'bewertung' not in ascents_df.columns:
            ascents_df['bewertung'] = 0
        else:
            ascents_df['bewertung'] = pd.to_numeric(ascents_df['bewertung'], errors='coerce').fillna(0).astype(int)

        # --- Handling für 'stern' in routes_df ---
        if 'stern' not in routes_df.columns:
            st.warning("Debugging: Spalte 'stern' NICHT in der 'routes'-Tabelle gefunden. Füge Dummy-Spalte hinzu (False).")
            routes_df['stern'] = False
        else:
            routes_df['stern'] = routes_df['stern'].astype(bool)

        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df 'stern' unique values: {routes_df['stern'].unique()}")
        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df 'stern' dtype: {routes_df['stern'].dtype}")
        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df count of True in 'stern': {routes_df['stern'].sum()}")

        # --- Calculate 'is_done_route' for each route ---
        if 'route_id' in ascents_df.columns:
            done_route_ids = ascents_df['route_id'].unique().tolist()
            st.info(f"Debugging: {len(done_route_ids)} unique routes identified as 'done'.")
        else:
            st.warning("Column 'route_id' not found in ascents_df. 'Done' filter may not work correctly.")
            done_route_ids = []

        if 'route_id' in routes_df.columns:
            routes_df['is_done_route'] = routes_df['route_id'].isin(done_route_ids)
        else:
            st.error("Column 'route_id' not found in routes_df. Critical error for route linking.")
            routes_df['is_done_route'] = False

        # --- Bestimme für jeden PEAK, ob er mindestens EINE gemachte Route hat ---
        done_routes = routes_df[routes_df['is_done_route'] == True]
        done_peak_ids = done_routes['peak_id'].unique().tolist()
        peaks_df['has_done_route'] = peaks_df['peak_id'].isin(done_peak_ids)
        st.info(f"DEBUG IN FETCH_DATA: peaks_df 'has_done_route' unique values: {peaks_df['has_done_route'].unique()}")
        st.info(f"DEBUG IN FETCH_DATA: peaks_df count of True in 'has_done_route': {peaks_df['has_done_route'].sum()}")

        # NEU: Kommentar zum Peak mergen
        # Zuerst ascents mit routes mergen, um peak_id zu bekommen
        if not ascents_df.empty and 'route_id' in ascents_df.columns and 'peak_id' in routes_df.columns:
            ascents_with_peak_info = ascents_df.merge(routes_df[['route_id', 'peak_id']], on='route_id', how='left')
            
            # Wähle den ersten Kommentar pro Peak (wenn mehrere Ascents vorhanden sind)
            # Duplizierte peak_ids entfernen und den ersten Eintrag behalten
            ascents_with_peak_info_unique = ascents_with_peak_info.drop_duplicates(subset=['peak_id'], keep='first')
            
            # Merge den Kommentar in den peaks_df
            peaks_df = peaks_df.merge(ascents_with_peak_info_unique[['peak_id', 'kommentar']], on='peak_id', how='left')
            
            # Fülle NaN-Werte für 'kommentar' mit einem leeren String auf
            peaks_df['kommentar'] = peaks_df['kommentar'].fillna("").astype(str)
        else:
            st.warning("Could not merge 'kommentar' into peaks_df. Check 'ascents_df' or 'routes_df' structure.")
            peaks_df['kommentar'] = "" # Dummy-Spalte, wenn Mergen fehlschlägt


        return peaks_df, routes_df, ascents_df
    except Exception as e:
        st.error(f"Error loading data from Supabase: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def make_triangle(lat, lon, size=0.001):
    if pd.isna(lat) or pd.isna(lon) or pd.isna(size) or size <= 0:
        return None
    try:
        return [
            [lat + size, lon],
            [lat - size / 2, lon - size * math.sqrt(3)/2],
            [lat - size / 2, lon + size * math.sqrt(3)/2],
        ]
    except TypeError:
        st.error(f"Error in make_triangle: lat={lat}, lon={lon}, size={size} are not valid numbers.")
        return None

def app():
    st.set_page_config(layout="wide")
    st.title("Gipfelbuch - Kletter-App")

    peaks_df, routes_df, ascents_df = fetch_data()

    if peaks_df.empty or routes_df.empty or ascents_df.empty:
        st.warning("No data available or error loading data. Please check your Supabase connection and tables.")
        st.stop()

    # 🔹 Berechne die Anzahl der Routen pro Peak
    if 'peak_id' in routes_df.columns and 'route_id' in routes_df.columns:
        route_counts = routes_df.groupby("peak_id").size().reset_index(name="anzahl_routen")
        peaks_df = peaks_df.merge(route_counts, on="peak_id", how="left")
        peaks_df["anzahl_routen"] = peaks_df["anzahl_routen"].fillna(0).astype(int)
    else:
        st.warning("Columns 'peak_id' or 'route_id' missing in 'routes_df', 'anzahl_routen' cannot be calculated.")
        peaks_df["anzahl_routen"] = 0

    # 🔹 Ermittle den maximalen Sternwert pro Peak
    if 'stern' in routes_df.columns and 'peak_id' in routes_df.columns:
        peak_has_star = routes_df.groupby('peak_id')['stern'].any().reset_index(name='peak_has_star')
        peaks_df = peaks_df.merge(peak_has_star, on='peak_id', how='left')
        peaks_df['peak_has_star'] = peaks_df['peak_has_star'].fillna(False).astype(bool)
        st.info(f"DEBUG APP: peaks_df 'peak_has_star' unique values: {peaks_df['peak_has_star'].unique()}")
        st.info(f"DEBUG APP: peaks_df count of True in 'peak_has_star': {peaks_df['peak_has_star'].sum()}")
    else:
        peaks_df['peak_has_star'] = False

    # 🔹 Bestimme die höchste Bewertung pro Peak
    if 'bewertung' in ascents_df.columns and 'route_id' in ascents_df.columns and 'peak_id' in routes_df.columns:
        ascents_with_peak_id = ascents_df.merge(routes_df[['route_id', 'peak_id']], on='route_id', how='left')
        max_bewertung_per_peak = ascents_with_peak_id.groupby('peak_id')['bewertung'].max().reset_index(name='max_bewertung_per_peak')
        peaks_df = peaks_df.merge(max_bewertung_per_peak, on='peak_id', how='left')
        peaks_df['max_bewertung_per_peak'] = peaks_df['max_bewertung_per_peak'].fillna(0).astype(int)
    else:
        peaks_df['max_bewertung_per_peak'] = 0


    # 2. Filteroptionen
    st.sidebar.title("Filter Options")

    gebiet_filter_options = sorted(peaks_df['gebiet'].unique().tolist())
    if len(gebiet_filter_options) > 0:
        gebiet_filter = st.sidebar.selectbox('Select an area', options=['All Areas'] + gebiet_filter_options)
    else:
        st.sidebar.warning("No areas available for filtering.")
        gebiet_filter = 'All Areas'

    schwierigkeit_filter = st.sidebar.selectbox(
        'Select Difficulty',
        options=["All Ratings", "Easy", "Okay", "Hard"]
    )
    difficulty_filter_value = None
    if schwierigkeit_filter != "All Ratings":
        difficulty_filter_value = {
            "Easy": 1,
            "Okay": 2,
            "Hard": 3
        }[schwierigkeit_filter]

    sternchen_filter = st.sidebar.radio(
        "Select routes with or without a star",
        options=["All", "Has Star", "No Star"]
    )
    if sternchen_filter == "Has Star":
        sternchen_filter_value = True
    elif sternchen_filter == "No Star":
        sternchen_filter_value = False
    else:
        sternchen_filter_value = None

    if 'hoehe' in peaks_df.columns and pd.api.types.is_numeric_dtype(peaks_df['hoehe']):
        min_hoehe = int(peaks_df['hoehe'].min()) if not peaks_df['hoehe'].empty and pd.notna(peaks_df['hoehe'].min()) else 0
        max_hoehe = int(peaks_df['hoehe'].max()) if not peaks_df['hoehe'].empty and pd.notna(peaks_df['hoehe'].max()) else 3000
        hoehe_filter = st.sidebar.slider('Select maximum rock height in meters', min_value=min_hoehe, max_value=max_hoehe, step=10, value=max_hoehe)
    else:
        st.sidebar.warning("Height filter not available as 'hoehe' column is missing or not numeric.")
        hoehe_filter = None

    gemacht_filter = st.sidebar.checkbox('Show climbed routes')

    # 3. Apply Filters - Startet mit peaks_df
    st.info(f"DEBUG FILTER START: filtered_peaks rows (before any filters): {len(peaks_df)}")
    filtered_peaks = peaks_df.copy()

    # Gebiet Filter
    st.info(f"DEBUG FILTER GEBIET (before): rows: {len(filtered_peaks)}")
    if gebiet_filter != 'All Areas':
        filtered_peaks = filtered_peaks[filtered_peaks['gebiet'] == gebiet_filter]
    st.info(f"DEBUG FILTER GEBIET (after): rows: {len(filtered_peaks)}")

    # Difficulty Filter
    st.info(f"DEBUG FILTER DIFFICULTY (before): rows: {len(filtered_peaks)}")
    if difficulty_filter_value is not None:
        if 'max_bewertung_per_peak' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['max_bewertung_per_peak'] == difficulty_filter_value]
        else:
            st.warning("Column 'max_bewertung_per_peak' not found, difficulty filter ignored.")
    st.info(f"DEBUG FILTER DIFFICULTY (after): rows: {len(filtered_peaks)}")

    # Star Filter
    st.info(f"DEBUG FILTER STAR (before): rows: {len(filtered_peaks)}")
    if sternchen_filter_value is not None:
        if 'peak_has_star' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['peak_has_star'] == sternchen_filter_value]
            st.info(f"DEBUG AFTER 'peak_has_star' filter: rows: {len(filtered_peaks)}")
        else:
            st.warning("Column 'peak_has_star' not found, star filter ignored.")
    st.info(f"DEBUG FILTER STAR (after): rows: {len(filtered_peaks)}")

    # Height Filter
    st.info(f"DEBUG FILTER HEIGHT (before): rows: {len(filtered_peaks)}")
    if hoehe_filter is not None and 'hoehe' in filtered_peaks.columns:
        filtered_peaks = filtered_peaks[pd.to_numeric(filtered_peaks['hoehe'], errors='coerce').fillna(0) <= hoehe_filter]
    st.info(f"DEBUG FILTER HEIGHT (after): rows: {len(filtered_peaks)}")

    # 'Done' Filter
    st.info(f"DEBUG FILTER DONE (before): rows: {len(filtered_peaks)}")
    if gemacht_filter:
        if 'has_done_route' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['has_done_route'] == True]
            st.info(f"Debugging: {len(filtered_peaks)} peaks contain done routes after filter.")
        else:
            st.warning("Column 'has_done_route' missing. 'Done' filter ignored.")
    st.info(f"DEBUG FILTER DONE (after): rows: {len(filtered_peaks)}")
    
    # Debugging nach allen Filtern
    st.info(f"DEBUG AFTER ALL FILTERS (final count): filtered_peaks rows: {len(filtered_peaks)}")
    if 'peak_has_star' in filtered_peaks.columns:
        st.info(f"DEBUG AFTER ALL FILTERS: filtered_peaks 'peak_has_star' unique values: {filtered_peaks['peak_has_star'].unique()}")
    if 'has_done_route' in filtered_peaks.columns:
        st.info(f"DEBUG AFTER ALL FILTERS: filtered_peaks 'has_done_route' unique values: {filtered_peaks['has_done_route'].unique()}")


    # **Überprüfung und Bereinigung von NaN-Werten für Kartenplotting**
    initial_rows_for_plotting_check = len(filtered_peaks)
    
    cols_for_map = ['lat', 'lon', 'hoehe', 'gipfel', 'gebiet', 'anzahl_routen']
    if 'peak_has_star' in filtered_peaks.columns:
        cols_for_map.append('peak_has_star')
    if 'has_done_route' in filtered_peaks.columns:
        cols_for_map.append('has_done_route')
    # NEU: Auch 'kommentar' für die Plotting-Prüfung hinzufügen
    if 'kommentar' in filtered_peaks.columns:
        cols_for_map.append('kommentar')

    existing_cols_for_map = [col for col in cols_for_map if col in filtered_peaks.columns]
    
    if existing_cols_for_map:
        filtered_peaks = filtered_peaks.dropna(subset=existing_cols_for_map)
        if len(filtered_peaks) < initial_rows_for_plotting_check:
            st.warning(f"Es wurden {initial_rows_for_plotting_check - len(filtered_peaks)} Gipfel mit fehlenden Daten (Koordinaten, Höhe etc.) für die Kartenanzeige entfernt.")
    else:
        st.warning("Wichtige Spalten (lat, lon, hoehe) für die Kartenanzeige fehlen in 'filtered_peaks'.")
        filtered_peaks = pd.DataFrame() 

    st.info(f"DEBUG FINAL PLOTTING COUNT: rows after NaN drop for map: {len(filtered_peaks)}")

    # 5. Ausgabe der gefilterten Gebirgspunkte als Liste
    st.subheader("Gefilterte Gebirgspunkte")
    if not filtered_peaks.empty:
        display_columns = ['gipfel', 'gebiet', 'hoehe', 'anzahl_routen']
        if 'max_bewertung_per_peak' in filtered_peaks.columns:
            display_columns.append('max_bewertung_per_peak')
        if 'peak_has_star' in filtered_peaks.columns:
            display_columns.append('peak_has_star')
        if 'has_done_route' in filtered_peaks.columns:
            display_columns.append('has_done_route')
        # NEU: 'kommentar' zur Anzeige in der Tabelle hinzufügen
        if 'kommentar' in filtered_peaks.columns:
            display_columns.append('kommentar')

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
        st.info("No peaks available to center the map and display triangles.")
        return 

    # 7. Folium-Karte erstellen
    m = folium.Map(location=[lat_center, lon_center], zoom_start=11)

    # 8. Dreiecke als Polygone einfügen (Größe nach Höhe)
    drawn_triangles_count = 0
    for index, row in filtered_peaks.iterrows():
        required_cols_for_plot = ['lat', 'lon', 'hoehe', 'anzahl_routen', 'gipfel', 'gebiet']
        
        if 'peak_has_star' in row: required_cols_for_plot.append('peak_has_star')
        if 'has_done_route' in row: required_cols_for_plot.append('has_done_route')
        # NEU: Auch 'kommentar' prüfen
        if 'kommentar' in row: required_cols_for_plot.append('kommentar')


        if not all(col in row.index and pd.notna(row[col]) for col in required_cols_for_plot):
            continue 

        hoehe_val = pd.to_numeric(row["hoehe"], errors='coerce')
        if pd.isna(hoehe_val) or hoehe_val < 0: 
            continue

        größe = 0.0012 + (hoehe_val * 0.00011)
        if größe <= 0: 
            continue

        fill_color = "red" 
        
        if row.get('peak_has_star', False):
            fill_color = "purple"
        
        if row.get('has_done_route', False):
            fill_color = "black"

        coords = make_triangle(row["lat"], row["lon"], größe)
        if coords: 
            tooltip_text = f"""
            <b>{row['gipfel']}</b><br>
            Height: {int(hoehe_val)} m<br>
            Routes: {int(row['anzahl_routen'])}<br>
            Area: {row['gebiet']}
            """
            if 'peak_has_star' in row:
                tooltip_text += f"<br>Star: {'⭐' if row['peak_has_star'] else 'No'}"
            if 'has_done_route' in row:
                tooltip_text += f"<br>Climbed: {'✅' if row['has_done_route'] else '❌'}"
            
            # NEU: Kommentar zum Tooltip hinzufügen, falls vorhanden
            if 'kommentar' in row and row['kommentar']: # Prüft, ob Spalte existiert und Wert nicht leer ist
                tooltip_text += f"<br>Comment: {row['kommentar']}"


            folium.Polygon(
                locations=coords,
                color=None,
                fill=True,
                fill_color=fill_color,
                fill_opacity=0.89,
                tooltip=folium.Tooltip(tooltip_text, sticky=True)
            ).add_to(m)
            drawn_triangles_count += 1
        
    st.info(f"Number of triangles drawn on the map: {drawn_triangles_count}")

    st_data = st_folium(m, width=1400, height=600)

if __name__ == "__main__":
    app()