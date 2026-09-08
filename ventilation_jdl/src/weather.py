"""Einlesen der ortsgenauen Testreferenzjahre (TRY) des DWD (Stand 2017).

Referenz: DWD/BBR (2017) - Handbuch "Ortsgenaue Testreferenzjahre von
Deutschland fuer mittlere, extreme und zukuenftige Witterungsverhaeltnisse".

Jede TRY-Datei besteht aus einem Metadaten-Header, einer Zeile mit den
Parameterabkuerzungen (Spaltennamen) und 8760 Datenzeilen (eine je Stunde
des Jahres). Die genaue Spaltenreihenfolge kann sich zwischen TRY-Varianten
unterscheiden, deshalb wird die Kopfzeile in der Datei gesucht statt eine
feste Reihenfolge anzunehmen.
"""

from pathlib import Path

import pandas as pd

# Bekannte Parameterabkuerzungen laut TRY-Handbuch (Tab. 2), zur Erkennung
# der Kopfzeile mit Spaltennamen.
BEKANNTE_SPALTEN = {
    "RW", "HW", "MM", "DD", "HH", "N", "WR", "WG",
    "t", "p", "WD", "RF", "B", "D", "A", "E", "IL", "x",
}

SPALTE_TEMPERATUR = "t"
SPALTE_FEUCHTE = "x"    # Wasserdampfgehalt (Mischungsverhaeltnis) in g/kg trockener Luft
SPALTE_DRUCK = "p"      # Luftdruck in Stationshoehe in hPa


def _finde_kopfzeile(zeilen):
    """Sucht die Zeile mit den Parameterabkuerzungen (Spaltennamen)."""
    beste_zeile = None
    beste_treffer = 0
    for idx, zeile in enumerate(zeilen):
        tokens = zeile.split()
        if not tokens:
            continue
        treffer = sum(1 for tok in tokens if tok in BEKANNTE_SPALTEN)
        if treffer >= 5 and treffer > beste_treffer:
            beste_treffer = treffer
            beste_zeile = idx
    if beste_zeile is None:
        raise ValueError(
            "Konnte die Spaltennamenzeile in der TRY-Datei nicht finden. "
            "Bitte Dateiformat pruefen (DWD/BBR 2017)."
        )
    return beste_zeile


def try_datei_einlesen(pfad):
    """Liest eine DWD-TRY-Datei ein und gibt einen DataFrame mit 8760
    Stundenwerten zurueck (Index 1..8760, Spalten u. a. 't', 'x', 'p')."""
    pfad = Path(pfad)
    with pfad.open("r", encoding="latin-1") as f:
        zeilen = f.readlines()

    header_idx = _finde_kopfzeile(zeilen)
    spalten = zeilen[header_idx].split()

    daten_zeilen = zeilen[header_idx + 1:]
    daten_zeilen = [z for z in daten_zeilen if z.strip() and not set(z.strip()) <= {"*"}]

    zeilen_werte = [z.split() for z in daten_zeilen if len(z.split()) == len(spalten)]
    if len(zeilen_werte) < 8760:
        raise ValueError(
            f"Es wurden nur {len(zeilen_werte)} Datenzeilen gefunden, "
            "erwartet werden 8760 Stundenwerte. Bitte TRY-Datei pruefen."
        )
    zeilen_werte = zeilen_werte[:8760]

    df = pd.DataFrame(zeilen_werte, columns=spalten)
    df = df.apply(pd.to_numeric, errors="coerce")
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="stunde_des_jahres")

    if SPALTE_TEMPERATUR not in df.columns:
        raise ValueError("Spalte 't' (Lufttemperatur) nicht in der TRY-Datei gefunden.")
    return df


def aussentemperatur(df):
    """Stuendliche Aussenlufttemperatur (°C)."""
    return df[SPALTE_TEMPERATUR]


def absolute_humidity(df):
    """Stuendlicher Wasserdampfgehalt der Aussenluft (g/kg trockener Luft),
    direkt aus TRY-Spalte 'x' (siehe TRY-Handbuch, Tab. 2)."""
    if SPALTE_FEUCHTE not in df.columns:
        raise ValueError("Spalte 'x' (Wasserdampfgehalt) nicht in der TRY-Datei gefunden.")
    return df[SPALTE_FEUCHTE]


def air_pressure_pa(df):
    """Stuendlicher Luftdruck in Pa (TRY-Spalte 'p' liegt in hPa vor)."""
    if SPALTE_DRUCK not in df.columns:
        raise ValueError("Spalte 'p' (Luftdruck) nicht in der TRY-Datei gefunden.")
    return df[SPALTE_DRUCK] * 100.0
