# ventilation_jdl

Berechnet ueberschlaegig die Jahresenergiemenge der Lueftung eines
virtuellen Nichtwohngebaeudes (Heizen, Kuehlen, Befeuchten, Ventilatoren)
und erstellt die zugehoerige Jahresdauerlinie (JDL).

Grundlage: Randbedingungen nach DIN V 18599 (Teile 2, 3, 10),
Wetterdaten auf Basis der ortsgenauen Testreferenzjahre (TRY) des DWD
(Stand 2017).

## Ordnerstruktur

```
ventilation_jdl/
  main.py               Hauptprogramm - hier starten
  src/
    weather.py           Einlesen der TRY-Datensaetze
    building.py           Definition des virtuellen Gebaeudes
    ventilation.py         stuendliche Berechnung Heizen/Kuehlen/Befeuchten/Ventilatoren
    load_duration.py       Erstellung der Jahresdauerlinie
    kennwertverfahren.py   Vergleichsrechnung nach DIN V 18599-3 (Kennwertverfahren)
  data/
    try/                   TRY-Rohdaten (hier ablegen)
    profiles/               Gebaeudeprofile (JSON)
  results/                 Berechnungsergebnisse (CSV, Diagramme)
```

## Installation

```
pip install -r requirements.txt
```

## Nutzung

In `main.py` ganz oben die drei Pfade (TRY-Datei, Gebaeudeprofil,
Ausgabeordner) eintragen, dann:

```
python main.py
```

## Methodischer Ansatz

Fuer jede Stunde des TRY-Jahres wird die Lueftungsleistung ueber eine
einfache Energiebilanz berechnet:

    Q_h(t) = rho * c_p * V_dot_a(t) * (theta_i - theta_e(t))          Heizfall
    Q_c(t) = rho * c_p * V_dot_a(t) * (theta_e(t) - theta_i,c)         Kuehlfall

Eine vorhandene Waermerueckgewinnung wird ueber den
Temperaturaenderungsgrad eta_WRG beruecksichtigt. Zusaetzlich kann eine
latente Befeuchtungsleistung (CoolProp) sowie die elektrische
Ventilatorleistung (Druckerhoehung / Wirkungsgrad) berechnet werden,
sofern im Gebaeudeprofil entsprechende Werte hinterlegt sind.

Die stuendlichen Werte werden je Energieart zur Jahresenergiemenge
aufsummiert und absteigend sortiert zur Jahresdauerlinie zusammengefuehrt.

Dies ist ein ueberschlaegiges Verfahren und ersetzt nicht das
Kennwertverfahren nach DIN V 18599-3 (siehe `kennwertverfahren.py` fuer
die Vergleichsrechnung).
