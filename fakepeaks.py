import pandas as pd
import numpy as np
import random

# Start-ID für die Gipfel
start_peak_id = 50
num_fake_peaks = 500 # Anzahl der zu generierenden Felsen

# Regionale Grenzen für die Sächsische Schweiz (ungefähr)
# Diese Werte basieren auf einer schnellen Google-Suche für die Region
# und dem von dir gewünschten Längengrad 14.000
min_lat = 50.900
max_lat = 50.950
min_lon = 14.000
max_lon = 14.200 # Etwas mehr Varianz im Längengrad

# Liste möglicher Namensbestandteile für realistisch klingende Felsen
name_parts_prefix = ["Kleiner", "Großer", "Falken", "Bären", "Adler", "Schuster", "Mönchs", "Barbarine", "Wartturm", "Heide", "Teufels", "Zwergen", "Tisch", "Lilien", "Affen", "Schramm"]
name_parts_suffix = ["turm", "stein", "nadel", "kopf", "horn", "wand", "fels", "spitze", "grat", "wächter"]

# Generiere die Fake-Daten
data = []
for i in range(num_fake_peaks):
    peak_id = start_peak_id + i
    
    # Zufälliger Gipfelname
    gipfel = f"{random.choice(name_parts_prefix)}{random.choice(name_parts_suffix)}"
    if random.random() < 0.3: # Füge manchmal eine Zahl oder einen Zusatz hinzu
        gipfel += f" {random.randint(1, 3)}"
    elif random.random() < 0.2:
        gipfel += f" West" if random.random() < 0.5 else " Ost"

    lat = round(random.uniform(min_lat, max_lat), 6)
    lon = round(random.uniform(min_lon, max_lon), 6) # Verwende den min_lon als Startpunkt
    
    gebiet = random.choice(["Rathen", "Zschand"])
    hoehe = random.randint(5, 55)

    data.append([peak_id, gipfel, gebiet, hoehe, lat, lon])

# Erstelle einen DataFrame
fake_peaks_df = pd.DataFrame(data, columns=['peak_id', 'gipfel', 'gebiet', 'hoehe', 'lat', 'lon'])

# Speichere als CSV
csv_filename = 'fake_peaks.csv'
fake_peaks_df.to_csv(csv_filename, index=False)

print(f"'{num_fake_peaks}' Fake-Felsen wurden erfolgreich in '{csv_filename}' generiert.")