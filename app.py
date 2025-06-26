#import streamlit as st
#import matplotlib.pyplot as plt

#st.write("Matplotlib test")

import streamlit as st
from supabase import create_client, Client
import pandas as pd
import matplotlib.pyplot as plt
import os
import plotly.graph_objects as go
import numpy as np
from dotenv import load_dotenv


st.title(" This will be my gipfelbuch 3.0!")
st.title("Kletter-App - Test")
st.write("Gipfelliste aus Supabase:")

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Holen der Supabase-URL und des API-Schlüssels aus den Umgebungsvariablen
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Erstelle die Verbindung zu Supabase
supabase: Client = create_client(url, key)

# Daten holen
@st.cache_data
def fetch_data():
    peaks_df = pd.DataFrame(supabase.table("peaks").select("*").execute().data)
    routes_df = pd.DataFrame(supabase.table("routes").select("*").execute().data)
    ascents_df = pd.DataFrame(supabase.table("ascents").select("*").execute().data)
    return peaks_df, routes_df, ascents_df

def app():
    st.title("Gipfel-Statistik pro Gebiet")

    peaks_df, routes_df, ascents_df = fetch_data()

    # Überprüfe die Spaltennamen in peaks_df
    st.write("Spaltennamen in peaks_df:", peaks_df.columns)

    # Verknüpfungen: ascents → routes → peaks
    ascents_with_peak = (
        ascents_df
        .merge(routes_df, left_on="route_id", right_on="route_id")
        .merge(peaks_df, left_on="peak_id", right_on="peak_id")
    )

    # Wie viele verschiedene Gipfel wurden pro Gebiet bestiegen?
    if 'gebiet' in peaks_df.columns:
        bestiegene_peaks = ascents_with_peak.groupby("gebiet")["peak_id"].nunique()
    else:
        st.write("Spalte 'gebiet' nicht gefunden. Bitte überprüfen!")
        return

    # Wie viele gibt es insgesamt pro Gebiet?
    total_peaks = peaks_df.groupby("gebiet")["peak_id"].nunique()

    # Fehlende = Gesamt - Bestiegen
    fehlende_peaks = total_peaks - bestiegene_peaks
    fehlende_peaks = fehlende_peaks.fillna(total_peaks)  # Falls 0 bestiegen

    # Reindexiere, um sicherzustellen, dass alle Gebiete auch in fehlenden Peaks vorhanden sind
    fehlende_peaks = fehlende_peaks.reindex(total_peaks.index, fill_value=0)
    bestiegene_peaks = bestiegene_peaks.reindex(total_peaks.index, fill_value=0)

    # Sicherstellen, dass alle Arrays denselben Index haben
    gebiete = total_peaks.index

    # Balkendiagramm
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(gebiete, fehlende_peaks, color='red', label="Fehlend")  # Fehlende Gipfel in rot
    ax.barh(gebiete, bestiegene_peaks, color='green', label="Bestiegen")  # Bestiegene Gipfel in grün

    ax.set_xlabel("Anzahl Gipfel")
    ax.set_title("Gipfelübersicht pro Gebiet")
    ax.legend()

    st.pyplot(fig)



        # Berechnung der Anzahl der gekletterten Routen pro Gebiet
    gekletterte_routen = ascents_with_peak.groupby("gebiet")["route_id"].nunique()

    # Berechnung der Gesamtanzahl der Gipfel pro Gebiet
    total_peaks = peaks_df.groupby("gebiet")["peak_id"].nunique()

    # Erstelle eine Tabelle mit den gewünschten Informationen
    result_df = pd.DataFrame({
        'Gebiet': total_peaks.index,
        'Anzahl gekletterte Routen': gekletterte_routen,
        'Anzahl Gipfel': total_peaks
    })

    # Zeige die Tabelle in Streamlit
    st.write("Tabelle mit Gebieten, Anzahl gekletterter Routen und Anzahl der Gipfel:")
    st.dataframe(result_df)


if __name__ == "__main__":
    app()

def app():
    st.title("Gipfel-Statistik pro Gebiet")

    peaks_df, routes_df, ascents_df = fetch_data()

    st.write("Spaltennamen in peaks_df:", peaks_df.columns)

    ascents_with_peak = (
        ascents_df
        .merge(routes_df, left_on="route_id", right_on="route_id")
        .merge(peaks_df, left_on="peak_id", right_on="peak_id")
    )

    if 'gebiet' not in peaks_df.columns:
        st.write("Spalte 'gebiet' nicht gefunden. Bitte überprüfen!")
        return

    bestiegene_peaks = ascents_with_peak.groupby("gebiet")["peak_id"].nunique()
    total_peaks = peaks_df.groupby("gebiet")["peak_id"].nunique()
    fehlende_peaks = total_peaks - bestiegene_peaks
    fehlende_peaks = fehlende_peaks.fillna(total_peaks)
    fehlende_peaks = fehlende_peaks.reindex(total_peaks.index, fill_value=0)
    bestiegene_peaks = bestiegene_peaks.reindex(total_peaks.index, fill_value=0)
    gebiete = total_peaks.index

    # Matplotlib Plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(gebiete, fehlende_peaks, color='red', label="Fehlend")
    ax.barh(gebiete, bestiegene_peaks, color='green', label="Bestiegen")
    ax.set_xlabel("Anzahl Gipfel")
    ax.set_title("Gipfelübersicht pro Gebiet")
    ax.legend()
    st.pyplot(fig)

    # Pandas Plot
    st.subheader("Pandas Plot: Gekletterte Routen pro Gebiet")
    gekletterte_routen = ascents_with_peak.groupby("gebiet")["route_id"].nunique()
    result_df = pd.DataFrame({
        'Gebiet': total_peaks.index,
        'Anzahl gekletterte Routen': gekletterte_routen,
        'Anzahl Gipfel': total_peaks
    })
    result_df = result_df.fillna(0)
    st.dataframe(result_df)

    if not result_df.empty:
        plot_data = result_df.set_index("Gebiet")[["Anzahl gekletterte Routen", "Anzahl Gipfel"]]
        st.bar_chart(plot_data)

    # Plotly 3D-Gebirgsplot mit Kommentaren
    st.subheader("3D-Mountain mit Besucher-Kommentaren")

    x = np.linspace(0, 100, 100)
    y = np.linspace(0, 100, 100)
    x_grid, y_grid = np.meshgrid(x, y)
    z_grid = np.sin(x_grid / 10) * np.cos(y_grid / 10) * 20 + 50

    comments = [
        {"x": 20, "y": 30, "z": 60, "comment": "Amazing view!"},
        {"x": 80, "y": 70, "z": 55, "comment": "Saw a deer here."},
        {"x": 50, "y": 50, "z": 65, "comment": "Perfect spot for lunch."}
    ]

    fig3d = go.Figure()
    fig3d.add_trace(go.Surface(
        z=z_grid, x=x, y=y,
        colorscale='Viridis',
        opacity=0.8,
        showscale=False,
        hoverinfo='skip'
    ))
    fig3d.add_trace(go.Scatter3d(
        x=[c["x"] for c in comments],
        y=[c["y"] for c in comments],
        z=[c["z"] for c in comments],
        mode='markers',
        marker=dict(size=6, color='red'),
        text=[c["comment"] for c in comments],
        hoverinfo='text',
        name='Comments'
    ))
    fig3d.update_layout(
        title="3D Mountain Plot with Visitor Comments",
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
            bgcolor='white'
        ),
        margin=dict(l=0, r=0, t=30, b=0),
        showlegend=False
    )
    st.plotly_chart(fig3d, use_container_width=True)


#not working online