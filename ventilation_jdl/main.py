"""Hauptprogramm: berechnet die Jahresenergiemenge der Lueftung fuer ein
virtuelles Gebaeude und erstellt die zugehoerige Jahresdauerlinie (JDL).

Einfach die drei Pfade unten anpassen und das Skript ausfuehren:
    python main.py
"""

import sys
from pathlib import Path

# Damit die Module aus dem Ordner "src" importiert werden koennen.
sys.path.append(str(Path(__file__).parent / "src"))

from building import Gebaeude
from weather import try_datei_einlesen
from ventilation import (
    heizleistung_kw,
    kuehlleistung_kw,
    befeuchtungsleistung_kw,
    ventilatorleistung_kw,
    jahresenergiemenge_kwh,
)
from load_duration import jahresdauerlinie, volllaststunden, jdl_plotten


# ---------------------------------------------------------------------
# Hier die Eingaben anpassen
# ---------------------------------------------------------------------
TRY_DATEI = "data/try/TRY2015_521425073302_Jahr.dat"
PROFIL_DATEI = "data/profiles/serverraum.json"
AUSGABE_ORDNER = "results"


def main():
    ausgabe_ordner = Path(AUSGABE_ORDNER)
    ausgabe_ordner.mkdir(parents=True, exist_ok=True)

    # 1. Wetterdaten und Gebaeudeprofil einlesen
    wetter_df = try_datei_einlesen(TRY_DATEI)
    gebaeude = Gebaeude.aus_json(PROFIL_DATEI)
    print(f"Gebaeude: {gebaeude.name} ({gebaeude.nutzungsprofil})")

    # 2. Fuer jede Energieart die stuendliche Leistung berechnen
    energiearten = {
        "heizen": ("Heizen", heizleistung_kw),
        "kuehlen": ("Kuehlen", kuehlleistung_kw),
        "befeuchten": ("Befeuchten", befeuchtungsleistung_kw),
        "ventilatoren": ("Ventilatoren", ventilatorleistung_kw),
    }

    for schluessel, (bezeichnung, berechnungsfunktion) in energiearten.items():
        stuendliche_leistung = berechnungsfunktion(wetter_df, gebaeude)

        # 3. Jahresenergiemenge und Volllaststunden bestimmen
        jahresenergie = jahresenergiemenge_kwh(stuendliche_leistung)
        vlh = volllaststunden(stuendliche_leistung)

        # 4. Jahresdauerlinie erstellen
        jdl = jahresdauerlinie(stuendliche_leistung)

        # 5. Ergebnisse speichern
        stuendliche_leistung.to_csv(ausgabe_ordner / f"{gebaeude.name}_{schluessel}_stundenwerte.csv")
        jdl.to_csv(ausgabe_ordner / f"{gebaeude.name}_{schluessel}_jahresdauerlinie.csv")
        jdl_plotten(
            jdl,
            titel=f"Jahresdauerlinie {bezeichnung} - {gebaeude.name}",
            ausgabe_pfad=ausgabe_ordner / f"{gebaeude.name}_{schluessel}_jahresdauerlinie.png",
        )

        print(f"  Jahresenergiemenge {bezeichnung}: {jahresenergie:.0f} kWh")
        print(f"  Rechnerische Volllaststunden {bezeichnung}: {vlh:.0f} h")

    print(f"Ergebnisse gespeichert in: {ausgabe_ordner.resolve()}")


if __name__ == "__main__":
    main()
