# ventilation_jdl

Python-Tool zur überschlägigen Berechnung der Jahresenergiemenge der Lüftung
eines virtuellen Nichtwohngebäudes und zur Erstellung der zugehörigen
Jahresdauerlinie (JDL) der Lüftungswärmeverluste.

Grundlage: energetische Randbedingungen nach DIN V 18599 (Teile 2, 3, 10),
Wetterdaten auf Basis der ortsgenauen Testreferenzjahre (TRY) des DWD
(Stand 2017).

## Projektstruktur

```
ventilation_jdl/
  src/ventilation_jdl/
    weather.py         Einlesen der DWD-TRY-Datensätze
    building.py         Definition virtueller Gebäude / Nutzungsprofile
    ventilation.py       Stündliche Lüftungswärmeverlustberechnung
    load_duration.py    Erstellung der Jahresdauerlinie
    cli.py               Kommandozeilen-Einstieg
  data/
    try/                 TRY-Rohdaten (vom Nutzer abzulegen, s. DWD/BBR 2017)
    profiles/            Nutzungsprofile virtueller Gebäude (JSON)
  results/               Berechnungsergebnisse (CSV, Diagramme)
  tests/                 Unit-Tests
```

## Methodischer Ansatz

Für jede Stunde des TRY-Jahres wird der Lüftungswärmeverlust nach der
Bilanzgleichung 

$$
    Q̇_V(t) = ρ · c_p · \dot{V}_{a(t)} · (\theta_i − \theta_e(t))
$$

berechnet, sofern sich die Stunde innerhalb der Betriebszeit des Gebäudes
befindet. Eine ggf. vorhandene Wärmerückgewinnung wird über den
Temperaturänderungsgrad $\eta_{WRG}$ durch Reduktion der wirksamen
Temperaturdifferenz berücksichtigt:
$$
    \Delta \theta_{eff} = (1 − \eta_{WRG}) · (\theta_i − \theta_e(t)) \quad  für~~ \theta_e(t) < \theta_i
$$

Die stündlichen Werte werden zur Jahresenergiemenge $Q_V$ aufsummiert und
absteigend sortiert zur Jahresdauerlinie zusammengeführt.

Dies ist ein überschlägiges Verfahren (direkte Bilanzierung mit
Stundenmittelwerten der Außenlufttemperatur) und ersetzt nicht das
detaillierte Kennwertverfahren nach DIN V 18599-3, Abschnitt 4.4.1.

## Installation

```
pip install -r requirements.txt
```

## Nutzung

```
python -m ventilation_jdl.cli --try-file data/try/<TRY-Datei>.dat \
    --profile data/profiles/buerogebaeude.json \
    --output results/
```
