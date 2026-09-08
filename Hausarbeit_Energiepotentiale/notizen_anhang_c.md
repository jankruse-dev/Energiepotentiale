# Notiz: Verhältnis des Tool-Verfahrens zu DIN V 18599-3, Anhang C

Sammelnotiz, noch nicht in die Hausarbeit eingearbeitet.

## Was Anhang C (normativ) fordert

DIN V 18599-3, Abschnitt 4.4.2 ("Spezielle Anlagenkonzepte") erlaubt für nicht
durch die Variantenmatrix (Abschnitt 7) abgebildete Anlagen ein direktes
Stundenschrittverfahren – dieses "muss den Berechnungsgrundlagen und
Randbedingungen nach Anhang C folgen", sonst ist es nicht normkonform.

**Anhang C, C.1 (Allgemeines):**
- Nutzenergiebedarf = Summe der stündlichen kalorischen Leistungen aller
  Komponenten über den Berechnungszeitraum.
- Leistungswerte grundsätzlich für stationäre Zustände.
- Ergeben sich aus den thermodynamischen Zustandsänderungen feuchter Luft
  vom Außenluftzustand zum Zuluftzustand.

**Anhang C, C.2 (Verfahren und Randbedingungen):**
- Außenluftzustand: zwingend aus den TRY-Daten des DWD nach
  DIN V 18599-10:2018-09, Anhang E, **Region 4** (Potsdam-Referenzklima).
- Alle weiteren Zustandsgrößen der Außenluft bei konstant **100 kPa**
  Gesamtdruck.
- Zuluftzustand folgt aus Zulufttemperatur θv,mech und absoluter
  Zuluftfeuchte xv,mech.
- θv,mech frei wählbar, aber nur im Gültigkeitsbereich:
  **14 °C ≤ θv,mech ≤ 22 °C** (Gleichung C.1).
- xv,mech: keine freie Wahl, sondern feste Standardwerte nach **Tabelle C.1**:

  | Nutzungsanforderung | xv,mech Befeuchtung (g/kg) | xv,mech Entfeuchtung (g/kg) |
  |---|---|---|
  | keine Feuchteanforderung | x_ODA | x_ODA |
  | mit Toleranzbereich | 6,0 | 10,0 |
  | ohne Toleranzbereich | 8,0 | 8,0 |

## Abgleich mit dem Tool (ventilation_jdl)

Gemeinsamkeit (Grundprinzip): stündliche Bilanz, Zustandsänderung der Luft
vom Außenluft- zum Zuluft-/Raumzustand, Summation zur Jahresenergiemenge.

Abweichungen von Anhang C:

1. **Wetterdatengrundlage:** Tool verwendet die vom Nutzer gewählten,
   ortsgenauen TRY-Datensätze (DWD/BBR 2017) statt zwingend Region 4
   (Potsdam) nach DIN V 18599-10, Anhang E.
2. **Zulufttemperatur-Gültigkeitsbereich:** Tool rechnet in
   `ventilation.py` direkt gegen die reale Raum-Solltemperatur des
   Gebäudeprofils (z. B. θi,c = 24 °C beim Einzelbüro), ohne die
   14–22 °C-Beschränkung aus Gleichung C.1. Diese Beschränkung wurde
   bislang nur in der separaten Kennwertverfahren-Vergleichsrechnung
   (`kennwertverfahren.py`) berücksichtigt (dort Ersatzwert 22 °C statt
   24 °C).
3. **Zuluftfeuchte:** Tool verwendet einen projektspezifisch je Gebäude
   festgelegten Feuchte-Sollwert (`feuchte_soll_gpkg`), nicht die festen
   Standardwerte aus Tabelle C.1. (Zufällige Übereinstimmung: der für
   das Serverraum-Profil gewählte Wert 6,0 g/kg entspricht dem
   Tabellenwert "mit Toleranzbereich / Befeuchtung" – das ist aber nicht
   bewusst aus der Tabelle abgeleitet worden.)
4. **Luftdruck:** Tool nutzt den tatsächlichen TRY-Luftdruck (Spalte `p`)
   für die CoolProp-Enthalpieberechnung, nicht den in Anhang C
   festgelegten konstanten Wert von 100 kPa.

## Einordnung / Formulierungsvorschlag für die Hausarbeit

Das Tool ist im **Grundprinzip an Anhang C orientiert** (stündliche
Bilanzierung über die thermodynamische Zustandsänderung feuchter Luft),
erfüllt aber dessen **Randbedingungen nicht vollständig** und stellt daher
**keinen normkonformen Nachweis nach Anhang C** dar. Dies sollte explizit
als Einschränkung im Kapitel "Einordnung und Grenzen der überschlägigen
Methode" (Diskussion) ergänzt werden – zusätzlich zu den bereits
dokumentierten Einschränkungen bei Kühlfall (Gültigkeitsbereich
Kennwertverfahren) und Befeuchtung (fehlender Kennwertverfahren-Vergleich).

**Entscheidung (Jan, 07.09.2026):** Kein strikter Anhang-C-Modus. Das Tool
bleibt bewusst freier/flexibler (ortsgenaue TRY-Daten, reale
Raum-Solltemperaturen ohne 14–22 °C-Clamping, projektspezifische
Feuchte-Sollwerte statt Tabelle C.1). Die Abweichungen von Anhang C werden
in der Hausarbeit als dokumentierte, bewusste Vereinfachung dargestellt,
nicht als zu behebendes Defizit.

## Erinnerung: Geltungsbereich der Berechnung (nur Lüftung, keine Heizkörper)

Das Tool berechnet ausschließlich den Lüftungswärmeverlust/-bedarf
(Energie, um die angesaugte Außenluft von θ_e auf θ_i bzw. θ_i,c zu
bringen). Es unterstellt NICHT, dass die Lüftung die einzige
Wärmequelle des Gebäudes ist – Transmissionswärmeverluste über
Wände/Fenster und die Beheizung durch klassische Heizkörper,
Fußbodenheizung etc. nach DIN V 18599-2 sind nicht Teil der Berechnung
und werden komplett getrennt behandelt.

→ In der Hausarbeit explizit klarstellen (z. B. in Methodik oder
Diskussion/Grenzen), damit die Jahresenergiemenge aus dem Tool nicht
mit dem gesamten Gebäudeheizwärmebedarf verwechselt wird.

## Treibende Temperaturdifferenz im Tool: nur θe vs. Raum-Solltemperatur

Im Tool gibt es keine von der Raumtemperatur entkoppelte
Zulufttemperatur. Sowohl Heiz- als auch Kühlfall verwenden ausschließlich
die stündliche Differenz zwischen Außenlufttemperatur θe(t) und der
hinterlegten Raum-Solltemperatur (θi bzw. θi,c), reduziert um den
WRG-Faktor:

    Δθ_eff(t) = (1-η_WRG) · (θi - θe(t))          [Heizfall]
    Δθ_eff(t) = (1-η_WRG) · (θe(t) - θi,c)         [Kühlfall]

Es wird implizit unterstellt, dass die Zuluft exakt auf
Raum-Solltemperatur gebracht wird (θv,mech = θi). Das unterscheidet sich
vom Kennwertverfahren nach DIN V 18599-3, das mit einer eigenständigen
Zulufttemperatur θhc (eigener Gültigkeitsbereich 14-22 °C, unabhängig von
der realen Raumtemperatur) rechnet – deswegen musste in der
Vergleichsrechnung die reale Kühlsolltemperatur (24 °C) auf 22 °C
gekappt werden, im stündlichen Tool-Verfahren dagegen nicht.

Fehlende Aspekte durch diese Vereinfachung: keine Abbildung einer von
der Raumtemperatur abweichenden Zulufttemperaturregelung (z. B. kühlere
Zuluft zur Lastspitzenkappung), keine Kanal-/Verteilverluste zwischen
RLT-Gerät und Raum, keine Unterscheidung Misch-/Verdrängungslüftung.

→ Als weiterer Punkt in "Einordnung und Grenzen der überschlägigen
Methode" ergänzen, neben WRG/interne Lasten und Anhang-C-Abweichungen.

## Klargestellt: WRG im Kühlfall bleibt aktiv (kein Sommerbypass nötig)

Frage aufgekommen, ob im Kühlfall die WRG (Stichwort Sommerbypass)
eigentlich deaktiviert werden müsste. Prüfung ergab: nein, die aktuelle
Modellierung (WRG bleibt auch im Kühlfall aktiv) ist korrekt.

Beleg:
- DIN V 18599-2, Abschnitt 6.3.3.6: "Bei der Berechnung des
  Nutzenergiebedarfs für Kühlen ist die Zulufttemperatur θV,mech nach
  Gleichung (98) zu berücksichtigen." Gleichung (98) ist die
  WRG-Gleichung – die Norm schreibt die WRG-Berücksichtigung im
  Kühlfall also explizit vor.
- DIN V 18599-11 (Automatisierungsgrade, Wärmeübertrager, V-3-2-2 bis
  V-3-2-4) kennt den Sommerbypass ("Wärmerückgewinnung mit
  Sommer-/Winterumschaltung") tatsächlich als Regelungsstrategie,
  Begründung dort: "Ein zusätzliches Aufheizen durch die
  Wärmerückgewinnung in den Sommermonaten kann vermieden werden."

Auflösung des scheinbaren Widerspruchs: Der Sommerbypass adressiert die
Konstellation θe < θi (Außenluft kühler als Raumluft, z. B. Nachtkühlung/
freie Kühlung) – ohne Bypass würde der WÜT die kühle Zuluft mit der
wärmeren Abluft vorwärmen und die freie Kühlung konterkarieren. Der
Kühlfall im Tool tritt aber nur bei θe(t) > θi,c auf (Außenluft wärmer
als Raum-Kühlsolltemperatur); dort kühlt der WÜT die heiße Zuluft mit
der kühleren Abluft vor, was den Kühlbedarf reduziert – erwünscht, kein
Bypass-Fall. Die vom Sommerbypass betroffene Situation (θe < θi) taucht
im Kühlfall-Zweig des Tools also gar nicht auf (dort ist Q_c(t)=0).

→ Falls das Thema in der Diskussion/Grenzen-Sektion aufgegriffen wird:
mit diesen zwei Quellen belegen, dass WRG im Kühlfall aktiv bleiben
darf/soll.
