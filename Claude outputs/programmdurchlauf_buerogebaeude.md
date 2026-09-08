# Programmdurchlauf am Beispiel "Buerogebaeude"

Schritt-fuer-Schritt-Erklaerung, was `main.py` fuer das Profil
`data/profiles/buerogebaeude.json` tatsaechlich rechnet. Die Zahlenwerte
zu den Beispielstunden sind mit dem echten Code nachgerechnet.

## 0. Eingaben

**Gebaeudeprofil (`buerogebaeude.json`):**

| Parameter | Wert |
|---|---|
| Außenluftvolumenstrom V̇_a | 500 m³/h |
| Raum-Solltemperatur Heizen θ_i | 20 °C |
| Raum-Solltemperatur Kühlen θ_i,c | 24 °C |
| Betriebszeit | 7–18 Uhr, Mo–Fr |
| Wärmerückgewinnungsgrad η_WRG | 0,6 |
| Druckerhöhung Zuluft Δp_ZUL | 300 Pa |
| Druckerhöhung Abluft Δp_ABL | 250 Pa |
| Ventilatorwirkungsgrad η_V | 0,6 |

(Keine Befeuchtung hinterlegt – `feuchte_soll_gpkg` ist bei diesem Profil
nicht gesetzt, daher liefert die Befeuchtung für dieses Gebäude durchgehend 0 kW.)

**Wetterdaten:** stündliche TRY-Datei mit 8760 Zeilen, Spalten `t`
(Außenlufttemperatur), `x` (Wasserdampfgehalt), `p` (Luftdruck).

## Schritt 1: Wetterdaten und Gebäudeprofil einlesen

```python
wetter_df = try_datei_einlesen(TRY_DATEI)
gebaeude = Gebaeude.aus_json(PROFIL_DATEI)
```

`try_datei_einlesen()` sucht in der TRY-Datei die Kopfzeile mit den
Spaltennamen und liest die 8760 Datenzeilen in eine Tabelle ein.
`Gebaeude.aus_json()` liest das Profil und legt ein Objekt mit den oben
genannten Werten an.

## Schritt 2: Betriebsmaske berechnen

```python
betrieb = betriebsmaske(wetter_df, gebaeude)
```

Für jede der 8760 Stunden wird aus Monat/Tag der Wochentag bestimmt und
geprüft, ob die Stunde innerhalb der hinterlegten Betriebszeit (7–18 Uhr,
Mo–Fr) liegt. Ergebnis: eine Liste aus `True`/`False` je Stunde. Außerhalb
der Betriebszeit wird später überall 0 kW angesetzt, unabhängig von der
Außentemperatur – die Lüftungsanlage läuft schlicht nicht.

**Beispiel Stunde C – Dienstag, 2 Uhr nachts:** liegt außerhalb 7–18 Uhr
→ Heizen, Kühlen, Befeuchten und Ventilatoren liefern hier alle 0 kW.

## Schritt 3: Heizleistung berechnen

```python
heiz_kw = heizleistung_kw(wetter_df, gebaeude)
```

Formel:

    Δθ(t)     = θ_i − θ_e(t)                     (nur falls θ_e(t) < θ_i, sonst 0)
    Δθ_eff(t) = Δθ(t) · (1 − η_WRG)
    Q̇_h(t)    = ρ · c_p · V̇_a(t) · Δθ_eff(t)

mit ρ = 1,20 kg/m³, c_p = 1,005 kJ/(kg·K) (Stoffwerte trockener Luft bei
ca. 20 °C). Die Wärmerückgewinnung reduziert die wirksame
Temperaturdifferenz, die tatsächlich beheizt werden muss.

**Beispiel Stunde A – Wintertag, 10 Uhr, θ_e = −5 °C (innerhalb Betrieb):**

    Δθ     = 20 − (−5) = 25 K
    Δθ_eff = 25 · (1 − 0,6) = 10 K
    Q̇_h    = 1,20 · 1,005 · (500/3600) · 10 = 1,675 kW

Die Wärmerückgewinnung "spart" hier 15 der 25 K ein – ohne WRG wäre die
Heizleistung 2,5-mal so hoch (4,19 kW).

## Schritt 4: Kühlleistung berechnen

```python
kuehl_kw = kuehlleistung_kw(wetter_df, gebaeude)
```

Formel (analog, mit umgekehrtem Vorzeichen):

    Δθ(t)     = θ_e(t) − θ_i,c                    (nur falls θ_e(t) > θ_i,c, sonst 0)
    Δθ_eff(t) = Δθ(t) · (1 − η_WRG)
    Q̇_c(t)    = ρ · c_p · V̇_a(t) · Δθ_eff(t)

**Beispiel Stunde B – Sommertag, 14 Uhr, θ_e = 29 °C (innerhalb Betrieb):**

    Δθ     = 29 − 24 = 5 K
    Δθ_eff = 5 · (1 − 0,6) = 2 K
    Q̇_c    = 1,20 · 1,005 · (500/3600) · 2 = 0,335 kW

Wenn keine Kühl-Solltemperatur im Profil hinterlegt wäre, würde die
Funktion sofort 0 kW für alle Stunden zurückgeben, ohne zu rechnen.

## Schritt 5: Befeuchtungsleistung berechnen

```python
befeuchtung_kw = befeuchtungsleistung_kw(wetter_df, gebaeude)
```

Für das Bürogebäude ist kein Feuchte-Sollwert hinterlegt → die Funktion
liefert direkt 0 kW für alle 8760 Stunden. Zur Illustration der Formel
trotzdem ein Rechenbeispiel mit dem Serverraum-Profil (dort ist
x_soll = 6 g/kg, θ_i = 21 °C hinterlegt):

    h_soll   = h(θ_i, x_soll)                      – Enthalpie feuchter Luft bei Zulufttemperatur und Soll-Feuchte
    h_e(t)   = h(θ_i, x_e(t))                      – Enthalpie bei Zulufttemperatur und Außenluftfeuchte
    Δh(t)    = max(h_soll − h_e(t), 0)
    Q̇_st(t)  = ṁ_tL · Δh(t)                        mit ṁ_tL = ρ · V̇_a(t)

h wird mit der Bibliothek CoolProp berechnet (spezifische Enthalpie
feuchter Luft je kg trockener Luft), nicht mit einer eigenen Näherung.

**Beispiel Stunde D – trockene Winterluft, x_e = 2 g/kg (Serverraum-Profil):**

    h_soll  = 36 142 J/kg   (bei 21 °C, 6 g/kg)
    h_e     = 26 150 J/kg   (bei 21 °C, 2 g/kg)
    Δh      = 9 992 J/kg
    Q̇_st    = (1,20 · (1500/3600)) · 9 992 / 1000 = 4,996 kW

Je trockener die Außenluft im Vergleich zum Soll, desto mehr Energie
muss für die Befeuchtung aufgewendet werden.

## Schritt 6: Ventilatorleistung berechnen

```python
ventilator_kw = ventilatorleistung_kw(wetter_df, gebaeude)
```

Formel:

    P_V(t) = V̇_a(t) · (Δp_ZUL + Δp_ABL) / η_V              (während Betriebszeit, sonst 0)

Anders als bei Heizen/Kühlen/Befeuchten hängt die Ventilatorleistung
nicht von der Außentemperatur ab, sondern nur davon, ob die Anlage läuft.

**Beispiel (gültig für jede Betriebsstunde, z. B. Stunde A oder B):**

    P_V = (500/3600) · (300 + 250) / 0,6 = 127,3 W = 0,127 kW

## Schritt 7: Jahresenergiemenge und Volllaststunden

```python
jahresenergie = jahresenergiemenge_kwh(stuendliche_leistung)
vlh = volllaststunden(stuendliche_leistung)
```

    Q_Jahr = Σ Q̇(t)  über alle 8760 Stunden          (Summe kW-Werte = kWh, da Zeitschritt 1 h)
    VLH    = Q_Jahr / max(Q̇(t))                       (rechnerische Volllaststunden)

Die Jahresenergiemenge ist einfach die Summe aller Stundenwerte. Die
Volllaststunden sagen: "Wie viele Stunden müsste die Anlage bei
Spitzenlast laufen, um dieselbe Jahresenergiemenge zu erreichen?"

## Schritt 8: Jahresdauerlinie (JDL) erstellen

```python
jdl = jahresdauerlinie(stuendliche_leistung)
jdl_plotten(jdl, ...)
```

Die 8760 Stundenwerte werden absteigend sortiert. Auf der x-Achse steht
dann nicht mehr die Uhrzeit, sondern die Anzahl der Jahresstunden, in
denen mindestens dieser Leistungswert erreicht wird. So sieht man auf
einen Blick, wie oft hohe Lasten auftreten – wichtig z. B. für die
Dimensionierung der Anlage.

## Schritt 9: Ergebnisse speichern

Für jede der vier Energiearten (Heizen, Kühlen, Befeuchten, Ventilatoren)
werden drei Dateien im Ausgabeordner abgelegt:

- `Einzelbuero_<art>_stundenwerte.csv` – alle 8760 Stundenwerte
- `Einzelbuero_<art>_jahresdauerlinie.csv` – sortierte JDL-Werte
- `Einzelbuero_<art>_jahresdauerlinie.png` – JDL-Diagramm

Zusätzlich gibt die Konsole Jahresenergiemenge und Volllaststunden je
Energieart aus.
