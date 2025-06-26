import pandas as pd
import random
from datetime import datetime, timedelta
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen für Supabase-Zugriff
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Fehler: SUPABASE_URL oder SUPABASE_KEY wurden nicht gefunden. Stellen Sie sicher, dass Ihre .env-Datei korrekt ist.")
    exit()

try:
    supabase: Client = create_client(url, key)
except Exception as e:
    print(f"Fehler beim Erstellen des Supabase-Clients: {e}")
    exit()

# --- Funktion, um die nächste freie ID zu finden ---
def get_next_available_id(table_name, id_column_name):
    try:
        response = supabase.table(table_name).select(id_column_name).order(id_column_name, desc=True).limit(1).execute()
        if response.data:
            max_id = response.data[0][id_column_name]
            return max_id + 1
        else:
            return 1 # Start with 1 if table is empty
    except Exception as e:
        print(f"Fehler beim Abrufen der höchsten ID aus {table_name}: {e}")
        return 1 # Fallback to 1

# --- Definition der Peaks aus deiner Eingabe ---
# Dies ist der String der Peaks, für die du Routen generieren möchtest.
# Ich gehe davon aus, dass diese Peaks bereits in deiner Supabase 'peaks'-Tabelle existieren.
peaks_data_string = """
peak_id,gipfel,gebiet,lat,lon,hoehe
124,Schrammstein,Zschand,50.939717,14.145871,45
125,Lilienturm,Rathen,50.945052,14.036273,40
126,Barbarinegrat,Rathen,50.946299,14.122072,17
127,Tischgrat 2,Rathen,50.916647,14.125908,37
128,Adlergrat 1,Rathen,50.925355,14.139739,17
129,Schrammspitze,Zschand,50.913616,14.193423,54
130,Schrammwächter,Zschand,50.946167,14.124709,47
131,Lilienkopf,Zschand,50.936806,14.171845,6
132,Tischwand,Zschand,50.913183,14.008562,9
133,Schustergrat 3,Zschand,50.919125,14.176914,21
134,Mönchsfels Ost,Rathen,50.91442,14.022514,16
135,Zwergenhorn,Rathen,50.911753,14.12573,38
136,Bärenwand,Rathen,50.929804,14.169988,15
137,Wartturmwächter,Rathen,50.925664,14.166439,39
138,Mönchswächter,Zschand,50.92532,14.024989,43
140,Adlerstein 1,Zschand,50.902674,14.146841,32
141,Kleinerspitze 2,Rathen,50.92548,14.138638,5
142,Tischhorn,Zschand,50.949407,14.141778,8
143,Zwergenturm 3,Zschand,50.940747,14.160628,50
144,Affenkopf,Zschand,50.916858,14.034622,16
145,Heidewand,Zschand,50.948596,14.059061,26
146,Barbarinegrat,Zschand,50.936996,14.095602,10
"""
from io import StringIO
peaks_df_specific = pd.read_csv(StringIO(peaks_data_string))
print(f"Lese {len(peaks_df_specific)} spezifische Peaks aus dem bereitgestellten Text.")


# --- Konfiguration für Routen und Ascents ---
routes_per_peak_choices = [2, 4] # Zufällig 2 oder 4 Routen pro Peak
star_probability = 0.2          # 20% Chance, dass eine Route einen Stern hat
ascent_probability = 0.3        # 30% Chance, dass eine NEU generierte Route als "gemacht" markiert wird

dummy_climber_id = "your_dummy_climber_id_here" # ERSETZE DIES MIT EINER ECHTEN CLIMBER_ID AUS DEINER DB, WENN NÖTIG!

# Liste möglicher Routennamen-Bestandteile
route_parts_prefix = ["Alter", "Neuer", "Direkter", "Schiefer", "Gelber", "Roter", "Blauer", "Steiler", "Leichter", "Großer"]
route_parts_suffix = ["weg", "riß", "kamin", "kante", "quergang", "stieg", "linie", "verschneidung", "aufstieg", "traverse"]

# Römische Ziffern für 'grad' (nicht für DB, nur zur Info)
roman_numerals = {
    1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V',
    6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'
}

# --- 1. Höchste vorhandene IDs abrufen ---
current_route_id = get_next_available_id("routes", "route_id")
current_ascent_id = get_next_available_id("ascents", "ascent_id")

print(f"Nächste freie route_id startet bei: {current_route_id}")
print(f"Nächste freie ascent_id startet bei: {current_ascent_id}")


# --- 2. Generiere Routen für die spezifischen Peaks ---
new_routes_data = []
generated_route_ids = [] # Speichert die IDs der neu generierten Routen

for _, peak_row in peaks_df_specific.iterrows():
    num_routes_for_this_peak = random.choice(routes_per_peak_choices)
    
    for i in range(num_routes_for_this_peak):
        route_id = current_route_id
        peak_id = peak_row['peak_id']
        
        name = f"{random.choice(route_parts_prefix)} {random.choice(route_parts_suffix)}"
        bewertung = random.randint(1, 10) # Entspricht grad_value
        stern = random.random() < star_probability

        new_routes_data.append([route_id, peak_id, name, bewertung, stern])
        generated_route_ids.append(route_id) # Diese Route wurde jetzt generiert
        current_route_id += 1

# Erstelle DataFrame für die neuen Routen
append_routes_df = pd.DataFrame(new_routes_data, columns=['route_id', 'peak_id', 'name', 'bewertung', 'stern'])
append_routes_df.to_csv('append_routes.csv', index=False)
print(f"'{len(append_routes_df)}' neue Routen wurden für die spezifischen Peaks in 'append_routes.csv' generiert.")


# --- 3. Generiere Ascents für einen Teil der NEUEN Routen ---
new_ascents_data = []

# Iteriere nur über die Routen, die wir gerade generiert haben
for _, route_row in append_routes_df.iterrows():
    if random.random() < ascent_probability:
        ascent_id = current_ascent_id
        route_id = route_row['route_id']
        
        # Zufälliges Datum in den letzten 2 Jahren
        days_ago = random.randint(1, 730)
        ascent_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        # Stelle sicher, dass 'climber_id' und 'bewertung' Spalten in deiner 'ascents'-Tabelle existieren
        # und die Typen übereinstimmen.
        new_ascents_data.append([ascent_id, route_id, ascent_date, dummy_climber_id, route_row['bewertung']])

        current_ascent_id += 1

# Erstelle DataFrame für die neuen Ascents
append_ascents_df = pd.DataFrame(new_ascents_data, columns=['ascent_id', 'route_id', 'date', 'climber_id', 'bewertung'])
append_ascents_df.to_csv('append_ascents.csv', index=False)
print(f"'{len(append_ascents_df)}' neue Ascents wurden für die generierten Routen in 'append_ascents.csv' generiert.")

print("\n--- Import-Anleitung für Supabase ---")
print("1. Gehe in deinem Supabase-Projekt zum 'Table Editor'.")
print(f"2. Wähle die 'routes'-Tabelle. Klicke auf 'Insert' -> 'Upload CSV' und wähle die Datei 'append_routes.csv'.")
print("   Stelle sicher, dass 'route_id', 'peak_id', 'name', 'bewertung', 'stern' korrekt zugeordnet werden.")
print("   Supabase sollte neue Zeilen hinzufügen, ohne bestehende zu löschen.")
print(f"3. Wähle die 'ascents'-Tabelle. Klicke auf 'Insert' -> 'Upload CSV' und wähle die Datei 'append_ascents.csv'.")
print("   Stelle sicher, dass 'ascent_id', 'route_id', 'date', 'climber_id', 'bewertung' korrekt zugeordnet werden.")
print("   Auch hier sollten neue Zeilen hinzugefügt werden.")
print("\nNach dem Import starte deine Streamlit-App neu.")