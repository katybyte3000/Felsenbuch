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
        ascents_df = pd.DataFrame(supabase.table("ascents").select("*").execute().data)

        # --- Handling für 'bewertung' in ascents_df ---
        if 'bewertung' not in ascents_df.columns:
            st.warning("Debugging: Spalte 'bewertung' NICHT in der 'ascents'-Tabelle gefunden. Füge Dummy-Spalte hinzu.")
            ascents_df['bewertung'] = 0
        else:
            ascents_df['bewertung'] = pd.to_numeric(ascents_df['bewertung'], errors='coerce').fillna(0).astype(int)

        # --- Handling für 'stern' in routes_df (da du sagtest, es ist auch dort) ---
        if 'stern' not in routes_df.columns:
            st.warning("Debugging: Spalte 'stern' NICHT in der 'routes'-Tabelle gefunden. Füge Dummy-Spalte hinzu (False).")
            routes_df['stern'] = False # Default auf False setzen
        else:
            # Stelle sicher, dass 'stern' boolesch ist.
            routes_df['stern'] = routes_df['stern'].astype(bool)

        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df 'stern' unique values: {routes_df['stern'].unique()}")
        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df 'stern' dtype: {routes_df['stern'].dtype}")
        st.info(f"DEBUG IN FETCH_DATA (ROUTES): routes_df count of True in 'stern': {routes_df['stern'].sum()}")


        # --- Process 'done' based on ascents_df (bleibt gleich) ---
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

    # --- Debugging nach dem Fetch ---
    # st.info(f"DEBUG AFTER FETCH: ascents_df 'stern' unique values: {ascents_df['stern'].unique()}") # Diese Zeile ist jetzt irrelevant, da 'stern' nicht mehr von ascents kommt
    # st.info(f"DEBUG AFTER FETCH: ascents_df 'stern' dtype: {ascents_df['stern'].dtype}")
    # st.info(f"DEBUG AFTER FETCH: ascents_df count of True in 'stern': {ascents_df['stern'].sum()}")

    # 🔹 Verknüpfung der Tabellen
    if "route_id" in ascents_df.columns and "route_id" in routes_df.columns:
        # ascents_with_route_info soll alle Spalten von ascents_df enthalten,
        # PLUS 'peak_id', 'is_done_route' UND 'stern' von routes_df
        # Stelle sicher, dass 'stern' hier von routes_df hinzugefügt wird
        
        # Liste der Spalten, die von routes_df gemergt werden sollen
        cols_to_merge_from_routes = ['route_id', 'peak_id', 'is_done_route']
        if 'stern' in routes_df.columns:
            cols_to_merge_from_routes.append('stern')
        
        ascents_with_route_info = ascents_df.merge(
            routes_df[cols_to_merge_from_routes], # Dynamische Auswahl, jetzt mit 'stern'
            on="route_id",
            how="left"
        )
    else:
        st.error("Fehlende 'route_id' Spalte in ascents_df oder routes_df.")
        st.stop()

    # --- Debugging nach dem ersten Merge ---
    if 'stern' in ascents_with_route_info.columns:
        st.info(f"DEBUG AFTER MERGE 1 (ascents_with_route_info): 'stern' unique values: {ascents_with_route_info['stern'].unique()}")
        st.info(f"DEBUG AFTER MERGE 1 (ascents_with_route_info): 'stern' dtype: {ascents_with_route_info['stern'].dtype}")
        st.info(f"DEBUG AFTER MERGE 1 (ascents_with_route_info): count of True in 'stern': {ascents_with_route_info['stern'].sum()}")
    else:
        st.warning("DEBUG AFTER MERGE 1: 'stern' column NOT in ascents_with_route_info. This is critical if 'stern' is expected here.")


    if "peak_id" in ascents_with_route_info.columns and "peak_id" in peaks_df.columns:
        # Hier wird ascents_with_route_info (das jetzt 'stern' von routes_df haben sollte)
        # mit peaks_df gemergt. 'stern' sollte erhalten bleiben.
        ascents_with_peak = ascents_with_route_info.merge(
            peaks_df[['peak_id', 'gipfel', 'gebiet', 'hoehe', 'lat', 'lon']],
            on="peak_id",
            how="left"
        )
    else:
        st.error("Fehlende 'peak_id' Spalte nach erstem Merge oder in peaks_df.")
        st.stop()
    
    # --- Debugging nach dem zweiten Merge ---
    if 'stern' in ascents_with_peak.columns:
        st.info(f"DEBUG AFTER MERGE 2 (ascents_with_peak): 'stern' unique values: {ascents_with_peak['stern'].unique()}")
        st.info(f"DEBUG AFTER MERGE 2 (ascents_with_peak): 'stern' dtype: {ascents_with_peak['stern'].dtype}")
        st.info(f"DEBUG AFTER MERGE 2 (ascents_with_peak): count of True in 'stern': {ascents_with_peak['stern'].sum()}")
    else:
        st.warning("DEBUG AFTER MERGE 2: 'stern' column NOT in ascents_with_peak. This is critical if 'stern' is expected here.")


    # 🔹 Berechnung der Anzahl der Routen pro Peak (bleibt gleich)
    if 'peak_id' in routes_df.columns and 'route_id' in routes_df.columns:
        route_counts = routes_df.groupby("peak_id").size().reset_index(name="anzahl_routen")
        peaks_df = peaks_df.merge(route_counts, on="peak_id", how="left")
        peaks_df["anzahl_routen"] = peaks_df["anzahl_routen"].fillna(0).astype(int)
    else:
        st.warning("Columns 'peak_id' or 'route_id' missing in 'routes_df', 'anzahl_routen' cannot be calculated.")
        peaks_df["anzahl_routen"] = 0

    if 'anzahl_routen' not in ascents_with_peak.columns:
        ascents_with_peak = ascents_with_peak.merge(peaks_df[['peak_id', 'anzahl_routen']], on='peak_id', how='left')
        ascents_with_peak['anzahl_routen'] = ascents_with_peak['anzahl_routen'].fillna(0).astype(int)

    # 2. Filteroptionen (bleibt gleich)
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

    # 3. Filter anwenden
    filtered_peaks = ascents_with_peak.copy()

    # --- Debugging vor dem Stern-Filter ---
    st.info(f"DEBUG BEFORE FINAL FILTER: filtered_peaks rows: {len(filtered_peaks)}")
    if 'stern' in filtered_peaks.columns:
        st.info(f"DEBUG BEFORE FINAL FILTER: filtered_peaks 'stern' unique values: {filtered_peaks['stern'].unique()}")
        st.info(f"DEBUG BEFORE FINAL FILTER: filtered_peaks 'stern' dtype: {filtered_peaks['stern'].dtype}")
        st.info(f"DEBUG BEFORE FINAL FILTER: filtered_peaks count of True in 'stern': {filtered_peaks['stern'].sum()}")
    else:
        st.warning("DEBUG BEFORE FINAL FILTER: 'stern' column NOT in filtered_peaks.")


    if gebiet_filter != 'All Areas':
        filtered_peaks = filtered_peaks[filtered_peaks['gebiet'] == gebiet_filter]

    # Apply difficulty filter
    if difficulty_filter_value is not None:
        if 'bewertung' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['bewertung'] == difficulty_filter_value]
        else:
            st.warning("Column 'bewertung' not found in filtered peaks, difficulty filter ignored.")

    # Apply star filter
    if sternchen_filter_value is not None:
        if 'stern' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['stern'] == sternchen_filter_value]
            st.info(f"DEBUG AFTER 'stern' filter: rows: {len(filtered_peaks)}")
        else:
            st.warning("Column 'stern' not found in filtered peaks, star filter ignored.")

    # Apply height filter
    if hoehe_filter is not None and 'hoehe' in filtered_peaks.columns:
        filtered_peaks = filtered_peaks[pd.to_numeric(filtered_peaks['hoehe'], errors='coerce').fillna(0) <= hoehe_filter]

    # Apply 'Done' filter
    if gemacht_filter:
        if 'is_done_route' in filtered_peaks.columns:
            filtered_peaks = filtered_peaks[filtered_peaks['is_done_route'] == True]
            filtered_peaks = filtered_peaks.drop_duplicates(subset=['peak_id'])
            st.info(f"Debugging: {len(filtered_peaks)} peaks contain done routes after filter.")
        else:
            st.warning("Column 'is_done_route' missing. 'Done' filter ignored.")
    else:
        filtered_peaks = filtered_peaks.drop_duplicates(subset=['peak_id'])
        st.info(f"Debugging: {len(filtered_peaks)} peaks are visible as 'Done' filter is off.")

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
        display_columns = ['gipfel', 'gebiet', 'hoehe', 'anzahl_routen']
        if 'bewertung' in filtered_peaks.columns:
            display_columns.append('bewertung')
        if 'stern' in filtered_peaks.columns:
            display_columns.append('stern')

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
            Height: {int(hoehe_val)} m<br>
            Routes: {int(row['anzahl_routen'])}<br>
            Area: {row['gebiet']}
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
        
    st.info(f"Number of triangles drawn on the map: {drawn_triangles_count}")

    st_data = st_folium(m, width=1400, height=600)

if __name__ == "__main__":
    app()