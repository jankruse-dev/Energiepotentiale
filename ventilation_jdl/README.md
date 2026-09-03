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

Für jede Stunde des TRY-Jahres wird der sensible Lüftungswärme- bzw.
-kälteverlust nach der Bilanzgleichung

    Q̇_h(t) = ρ · c_p · V̇_a(t) · (θ_i − θ_e(t))          (Heizfall, θ_e(t) < θ_i)
    Q̇_c(t) = ρ · c_p · V̇_a(t) · (θ_e(t) − θ_i,c)         (Kühlfall, θ_e(t) > θ_i,c)

berechnet, sofern sich die Stunde innerhalb der Betriebszeit des Gebäudes
befindet. Eine ggf. vorhandene Wärmerückgewinnung wird über den
Temperaturänderungsgrad η_WRG durch Reduktion der wirksamen
Temperaturdifferenz berücksichtigt (analog für Heiz- und Kühlfall). Der
Kühlfall wird nur berechnet, wenn im Gebäudeprofil eine
Kühl-Solltemperatur `solltemperatur_kuehlung_c` hinterlegt ist.

Zusätzlich kann eine latente Befeuchtungsleistung berechnet werden, sofern
im Gebäudeprofil ein Mindest-Wasserdampfgehalt der Zuluft
`feuchte_soll_gpkg` hinterlegt ist:

    Q̇_st(t) = ṁ_tL · (h(θ_i, x_soll) − h(θ_i, x_e(t)))   für x_e(t) < x_soll

mit h = spezifischer Enthalpie feuchter Luft (berechnet mit der Bibliothek
CoolProp/HumidAirProp). Die Außenluftfeuchte x_e(t) wird direkt der
TRY-Spalte `x` entnommen.

Zusätzlich kann die elektrische Jahresenergiemenge der Zu- und
Abluftventilatoren berechnet werden, sofern im Gebäudeprofil
Druckerhöhungen und ein Ventilatorwirkungsgrad hinterlegt sind:

    P_V(t) = V̇_a · (Δp_ZUL + Δp_ABL) / η_V                    (während Betrieb, sonst 0)

Dies ist der Sonderfall konstanten Volumenstroms (keine VAV-Teillast) der
allgemeinen Ventilatorleistungsgleichung nach DIN V 18599-3, Gl. (15)/(16).

Die stündlichen Werte werden je Energieart (Heizen/Kühlen/Befeuchten/
Ventilatoren) zur
Jahresenergiemenge aufsummiert und absteigend sortiert zur jeweiligen
Jahresdauerlinie zusammengeführt.

Dies ist ein überschlägiges Verfahren (direkte Bilanzierung mit
Stundenmittelwerten) und ersetzt nicht das detaillierte Kennwertverfahren
nach DIN V 18599-3, Abschnitt 4.4.1.

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
