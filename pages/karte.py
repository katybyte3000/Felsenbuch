import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase_config import supabase  # Supabase-Verbindung
import math

# 💬 Überschrift
st.subheader("Karte aller Gipfel mit Routenanzahl (Dreiecks-Marker)")

# 🔹 1. Daten laden
peaks_df = pd.DataFrame(supabase.table("peaks").select("*").execute().data)
routes_df = pd.DataFrame(supabase.table("routes").select("*").execute().data)

# 🔹 2. Anzahl der Routen pro peak_id zählen
route_counts = routes_df.groupby("peak_id").size().reset_index(name="anzahl_routen")

# 🔹 3. Verknüpfen
peaks_df = peaks_df.merge(route_counts, on="peak_id", how="left")
peaks_df["anzahl_routen"] = peaks_df["anzahl_routen"].fillna(0).astype(int)

# 🔹 4. Kartenmittelpunkt berechnen
lat_center = peaks_df["lat"].mean()
lon_center = peaks_df["lon"].mean()

# 🔹 5. Folium-Karte erstellen
m = folium.Map(location=[lat_center, lon_center], zoom_start=11)

# 🔹 6. Hilfsfunktion: Dreieck-Koordinaten berechnen
def make_triangle(lat, lon, size=0.001):
    """
    Erzeuge 3 Koordinaten für ein gleichseitiges Dreieck
    Größe ca. 0.001 Grad = ~100 m
    """
    return [
        [lat + size, lon],  # Spitze nach oben
        [lat - size / 2, lon - size * math.sqrt(3)/2],
        [lat - size / 2, lon + size * math.sqrt(3)/2],
    ]

# 🔹 7. Dreiecke als Polygone einfügen
for _, row in peaks_df.iterrows():
    größe = 0.002 + row["anzahl_routen"] * 0.0012  # Dynamisch skalieren

    triangle_coords = make_triangle(row["lat"], row["lon"], größe)

    folium.Polygon(
        locations=triangle_coords,
        color="black",
        fill=True,
        fill_color="blue",
        fill_opacity=0.85,
        tooltip=f"{row['gipfel']} ({row['anzahl_routen']} Routen)"
    ).add_to(m)

# 🔹 8. Karte anzeigen
st_data = st_folium(m, width=1200, height=600)
