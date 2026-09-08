# Übersicht Inputs / Outputs – ventilation_jdl

## 1. Inputs

### 1.1 Kommandozeilen-Parameter (`cli.py`)

| Parameter | Bedeutung |
|---|---|
| `--try-file` | Pfad zur DWD-TRY-Datei (Wetterdaten) |
| `--profile` | Pfad zur Gebäudeprofil-JSON-Datei |
| `--output` | Ausgabeverzeichnis (Standard: `results/`) |

### 1.2 Wetterdaten aus der TRY-Datei (`weather.py`)

Pro Stunde des Jahres (8760 Zeilen), relevante Spalten:

| Spalte | Bedeutung | Einheit |
|---|---|---|
| `MM`, `DD`, `HH` | Monat, Tag, Stunde | – |
| `t` | Außenlufttemperatur | °C |
| `x` | Wasserdampfgehalt (Mischungsverhältnis) der Außenluft | g/kg trockener Luft |
| `p` | Luftdruck in Stationshöhe | hPa (wird intern in Pa umgerechnet) |

Weitere Spalten (`RF`, `WR`, `WG`, `N`, ...) sind in der Datei vorhanden, werden vom Tool aber nicht ausgewertet.

### 1.3 Gebäudeprofil (`building.py`, JSON-Datei)

| Feld | Bedeutung | Einheit | Pflicht? |
|---|---|---|---|
| `name` | Bezeichnung des virtuellen Gebäudes | – | ja |
| `nutzungsprofil` | Nutzungsprofil nach DIN V 18599-10 (z. B. "Einzelbüro") | – | ja |
| `aussenluftvolumenstrom_m3h` | Außenluftvolumenstrom | m³/h | ja |
| `solltemperatur_innen_c` | Raum-Solltemperatur (Heizfall) θi | °C | ja |
| `betriebszeit.start_stunde` / `end_stunde` | tägliche Betriebszeit | Stunde (0–24) | ja |
| `betriebszeit.wochentage` | Betriebstage (0=Mo … 6=So) | – | ja |
| `waermerueckgewinnungsgrad` | Temperaturänderungsgrad WRG, η_WRG | – (0–1) | nein (Default 0.0) |
| `solltemperatur_kuehlung_c` | Raum-Solltemperatur Kühlung θi,c | °C | nein (None = kein Kühlfall) |
| `feuchte_soll_gpkg` | Mindest-Wasserdampfgehalt Zuluft x_soll | g/kg | nein (None = keine Befeuchtung) |
| `druckerhoehung_zuluft_pa` | Druckerhöhung Zuluftventilator Δp_ZUL | Pa | nein (None = keine Ventilatorberechnung) |
| `druckerhoehung_abluft_pa` | Druckerhöhung Abluftventilator Δp_ABL | Pa | nein (None = keine Ventilatorberechnung) |
| `wirkungsgrad_ventilator` | Gesamtwirkungsgrad Ventilator/Motor/Antrieb η_V | – (0–1) | nein (None = keine Ventilatorberechnung) |

## 2. Zwischengrößen (intern berechnet)

| Größe | Funktion | Bedeutung |
|---|---|---|
| Betriebsmaske (True/False je Stunde) | `berechne_betriebsmaske()` | Ist das Gebäude in dieser Stunde in Betrieb? |

## 3. Outputs

### 3.1 Stündliche Leistungswerte (je Energieart), als pandas-Series

| Funktion | Ausgabegröße | Einheit | Bedingung |
|---|---|---|---|
| `stuendlicher_waermeverlust_kw()` | Heizleistung Q̇_h(t) | kW | immer |
| `stuendliche_kaelteleistung_kw()` | Kühlleistung Q̇_c(t) | kW | nur wenn `solltemperatur_kuehlung_c` gesetzt |
| `stuendliche_befeuchtungsleistung_kw()` | Befeuchtungsleistung Q̇_st(t) | kW | nur wenn `feuchte_soll_gpkg` gesetzt |
| `stuendliche_ventilatorleistung_kw()` | elektrische Ventilatorleistung P_V(t) | kW | nur wenn Δp_ZUL/ABL und η_V gesetzt |

### 3.2 Jahreswerte

| Funktion | Ausgabegröße | Einheit |
|---|---|---|
| `jahresenergiemenge_kwh()` | Jahresenergiemenge je Energieart (Summe der Stundenwerte) | kWh/a |
| `volllaststunden()` | rechnerische Volllaststunden (Jahresenergiemenge / Spitzenlast) | h |

### 3.3 Jahresdauerlinie

| Funktion | Ausgabegröße |
|---|---|
| `jahresdauerlinie()` | absteigend sortierte Stundenwerte (Series, Index = Jahresstunden 1–8760) |

### 3.4 Dateien im Output-Verzeichnis (je Energieart: Heizen / Kühlen / Befeuchten / Ventilatoren)

| Datei | Inhalt |
|---|---|
| `{Gebäude}_{art}_stundenwerte.csv` | 8760 Stundenwerte der Leistung (kW) |
| `{Gebäude}_{art}_jahresdauerlinie.csv` | sortierte JDL-Werte |
| `{Gebäude}_{art}_jahresdauerlinie.png` | JDL-Diagramm |

### 3.5 Konsolenausgabe

- Jahresenergiemenge je Energieart (kWh)
- rechnerische Volllaststunden je Energieart (h)
- Pfad zum Output-Verzeichnis
