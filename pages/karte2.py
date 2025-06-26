import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from supabase_config import supabase
import math

st.subheader("Karte der Gipfel – gefiltert nach Routen-Schwierigkeit")

# 🔹 Daten laden
peaks_df = pd.DataFrame(supabase.table("peaks").select("*").execute().data)
routes_df = pd.DataFrame(supabase.table("routes").select("*").execute().data)

# 🔹 Höhe konvertieren
peaks_df["hoehe"] = pd.to_numeric(peaks_df["hoehe"], errors="coerce").fillna(0)

# 🔹 Routenanzahl pro Gipfel
route_counts = routes_df.groupby("peak_id").size().reset_index(name="anzahl_routen")
peaks_df = peaks_df.merge(route_counts, on="peak_id", how="left")
peaks_df["anzahl_routen"] = peaks_df["anzahl_routen"].fillna(0).astype(int)

# 🔹 Dropdown-Filter: Schwierigkeitsgrad (grade)
alle_grades = sorted(routes_df["grad_value"].dropna().unique())
auswahl_grade = st.selectbox("Nur Gipfel mit Routen dieses Grades anzeigen:", ["Alle"] + alle_grades)

# 🔹 Filter nach grade anwenden
if auswahl_grade != "Alle":
    gefilterte_peaks = routes_df[routes_df["grad_value"] == auswahl_grade]["peak_id"].unique()
    peaks_df = peaks_df[peaks_df["peak_id"].isin(gefilterte_peaks)]

# 🔹 Dropdown-Filter für Gebiete
alle_gebiete = peaks_df["gebiet"].dropna().unique()
auswahl_gebiet = st.selectbox("Gebiet auswählen:", ["Alle"] + sorted(alle_gebiete.tolist()))
if auswahl_gebiet != "Alle":
    peaks_df = peaks_df[peaks_df["gebiet"] == auswahl_gebiet]

# 🔹 Kartenmittelpunkt
lat_center = peaks_df["lat"].mean()
lon_center = peaks_df["lon"].mean()

# 🔹 Karte erstellen
m = folium.Map(location=[lat_center, lon_center], zoom_start=11)

# 🔹 Hilfsfunktion Dreieck
def make_triangle(lat, lon, size=0.001):
    return [
        [lat + size, lon],
        [lat - size / 2, lon - size * math.sqrt(3) / 2],
        [lat - size / 2, lon + size * math.sqrt(3) / 2],
    ]

# 🔹 Dreiecke zeichnen
for _, row in peaks_df.iterrows():
    größe = 0.0012 + (row["hoehe"] * 0.00011)

    coords = make_triangle(row["lat"], row["lon"], größe)

    tooltip_text = f"""
    <b>{row['gipfel']}</b><br>
    Höhe: {row['hoehe']} m<br>
    Routen: {row['anzahl_routen']}
    """

    folium.Polygon(
        locations=coords,
        color=None,
        fill=True,
        fill_color="black",
        fill_opacity=0.89,
        tooltip=folium.Tooltip(tooltip_text, sticky=True)
    ).add_to(m)

# 🔹 Karte anzeigen
st_data = st_folium(m, width=1400, height=600)
