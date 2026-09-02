"""Einlesen der ortsgenauen Testreferenzjahre (TRY) des DWD (Stand 2017).

Referenz: DWD/BBR (2017) - Handbuch "Ortsgenaue Testreferenzjahre von
Deutschland für mittlere, extreme und zukünftige Witterungsverhältnisse".

Jede TRY-Datei besteht aus einem Metadaten-Header, einer Zeile mit den
Parameterabkürzungen (Spaltennamen) und 8760 Datenzeilen (eine je Stunde
des Jahres). Da sich die genaue Spaltenreihenfolge zwischen TRY-Varianten
unterscheiden kann, wird die Spaltennamenzeile aus der Datei selbst
ermittelt, anstatt eine feste Spaltenreihenfolge anzunehmen.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Bekannte Parameterabkürzungen laut TRY-Handbuch (Tab. 2), zur Erkennung
# der Kopfzeile mit Spaltennamen.
KNOWN_COLUMNS = {
    "RW", "HW", "MM", "DD", "HH", "N", "WR", "WG",
    "t", "p", "WD", "RF", "B", "D", "A", "E", "IL", "x",
}

TEMPERATURE_COLUMN = "t"


@dataclass
class TryMetadata:
    """Ausgewählte Metadaten aus dem TRY-Header."""
    quelle: str
    dateiname: str


def _find_header_line_index(lines: list[str]) -> int:
    """Sucht die Zeile mit den Parameterabkürzungen (Spaltennamen).

    Die Zeile wird daran erkannt, dass ein Großteil ihrer Token in
    ``KNOWN_COLUMNS`` enthalten ist.
    """
    best_index = None
    best_hits = 0
    for idx, line in enumerate(lines):
        tokens = line.split()
        if not tokens:
            continue
        hits = sum(1 for tok in tokens if tok in KNOWN_COLUMNS)
        if hits >= 5 and hits > best_hits:
            best_hits = hits
            best_index = idx
    if best_index is None:
        raise ValueError(
            "Konnte die Spaltennamenzeile in der TRY-Datei nicht "
            "identifizieren. Bitte Dateiformat prüfen (DWD/BBR 2017)."
        )
    return best_index


def read_try_file(path: str | Path) -> pd.DataFrame:
    """Liest eine DWD-TRY-Datei (Stand 2017) ein und gibt einen DataFrame
    mit 8760 Stundenwerten zurück.

    Parameters
    ----------
    path:
        Pfad zur TRY-ASCII-Datei.

    Returns
    -------
    pandas.DataFrame
        Index ``stunde_des_jahres`` (1..8760), Spalten entsprechend der in
        der Datei angegebenen Parameterabkürzungen (u. a. ``t`` für die
        Lufttemperatur in °C).
    """
    path = Path(path)
    with path.open("r", encoding="latin-1") as f:
        lines = f.readlines()

    header_idx = _find_header_line_index(lines)
    columns = lines[header_idx].split()

    data_lines = lines[header_idx + 1:]
    # Entfernt Trennzeilen (z. B. "***") und Leerzeilen vor den Daten.
    data_lines = [ln for ln in data_lines if ln.strip() and not set(ln.strip()) <= {"*"}]

    rows = [line.split() for line in data_lines if len(line.split()) == len(columns)]
    if len(rows) < 8760:
        raise ValueError(
            f"Es wurden nur {len(rows)} Datenzeilen gefunden, erwartet "
            "werden 8760 Stundenwerte. Bitte TRY-Datei prüfen."
        )
    rows = rows[:8760]

    df = pd.DataFrame(rows, columns=columns)
    df = df.apply(pd.to_numeric, errors="coerce")
    df.index = pd.RangeIndex(start=1, stop=len(df) + 1, name="stunde_des_jahres")

    if TEMPERATURE_COLUMN not in df.columns:
        raise ValueError(
            "Spalte 't' (Lufttemperatur) nicht in der TRY-Datei gefunden."
        )
    return df


def outdoor_temperature(df: pd.DataFrame) -> pd.Series:
    """Gibt die stündliche Außenlufttemperatur (°C) als Series zurück."""
    return df[TEMPERATURE_COLUMN]
