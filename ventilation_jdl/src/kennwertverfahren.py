"""Vergleichsrechnung nach dem Kennwertverfahren der DIN V 18599-3.

Dieses Modul implementiert AUSSCHLIESSLICH den für die Vergleichsrechnung
in der Hausarbeit benötigten Ausschnitt des Kennwertverfahrens
(Abschnitt 7.2 bis 7.5 der DIN V 18599-3): Umrechnung des jährlichen
Heiz- bzw. Kühlenergiekennwerts einer festen RLT-Anlagenvariante auf
eine frei wählbare Zulufttemperatur, tägliche Betriebszeit und Anzahl
jährlicher Betriebstage, anschließende Denormierung auf den
tatsächlichen Zuluftvolumenstrom (konstanter Volumenstrom,
Jahresverfahren nach Abschnitt 4.4.1 i.V.m. Tabelle A.1).

Referenz: DIN V 18599-3:2018-09, Gleichungen (27), (29), (30), (31),
(32), (34), (37), (39) und (42).

Die hier hinterlegten Energiekennwerte stammen aus Tabelle A.1
(Spezifische Energiekennwerte Gesamtjahr) der DIN V 18599-3 für
Variante 1 (keine Feuchteanforderung, WRG-Typ "keine", d. h. keine
Wärmerückgewinnung), Variante 3 (keine Feuchteanforderung,
Wärmerückgewinnung "nur Wärme", Wärmerückgewinnungsgrad 60 %) sowie für
Variante 21 (Feuchteanforderung "mit Toleranzbereich", Dampfbefeuchter,
Wärmerückgewinnung "nur Wärme", Wärmerückgewinnungsgrad 60 %) und wurden
manuell aus der Norm übernommen, NICHT berechnet oder geschätzt.

Für den Kühlfall gilt außerdem: Der Gültigkeitsbereich der
Umrechnungsgleichungen (31)/(32) ist auf Zulufttemperatur-Sollwerte von
14 °C bis 22 °C begrenzt. Reale Raum-Kühlsolltemperaturen nach
DIN V 18599-10 (z. B. 24 °C für ein Einzelbüro) liegen außerhalb dieses
Bereichs; eine Anwendung der Gleichungen darauf wäre eine unzulässige
Extrapolation. Für eine normkonforme Vergleichsrechnung wird daher der
obere Rand des Gültigkeitsbereichs (22 °C) als Zulufttemperatur-Sollwert
angesetzt, nicht die tatsächliche Raum-Kühlsolltemperatur.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tabelle A.1 (Gesamtjahr), Variante 1: keine Feuchteanforderung,
# WRG-Typ "keine" (keine Wärmerückgewinnung vorhanden).
# Basis: theta_v,mech = 18 °C; t_v,mech = 12 h; d_v,mech = 365 d.
VARIANTE_1_JAHR = {
    "qh_18C_12h": 10291.0,  # Wh/(m3/h)
    "gh_u": 924.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gh_o": 1150.0,         # Wh/(K*m3/h), Zulufttemperatur 18-22°C
    "qc_18C_12h": 2358.0,   # Wh/(m3/h)
    "gc_u": 855.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gc_o": 389.0,          # Wh/(K*m3/h), Zulufttemperatur 18-22°C
}

# Tabelle A.1 (Gesamtjahr), Variante 3: keine Feuchteanforderung,
# WRG-Typ "nur Wärme", Wärmerückgewinnungsgrad 60 %.
# Basis: theta_v,mech = 18 °C; t_v,mech = 12 h; d_v,mech = 365 d.
VARIANTE_3_JAHR = {
    "qh_18C_12h": 1148.0,   # Wh/(m3/h)
    "gh_u": 274.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gh_o": 783.0,          # Wh/(K*m3/h), Zulufttemperatur 18-22°C
    "qc_18C_12h": 2309.0,   # Wh/(m3/h)
    "gc_u": 856.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gc_o": 389.0,          # Wh/(K*m3/h), Zulufttemperatur 18-22°C
}

# Tabelle A.1 (Gesamtjahr), Variante 21: Feuchteanforderung "mit
# Toleranzbereich" (Dampfbefeuchter), WRG-Typ "nur Wärme",
# Wärmerückgewinnungsgrad 60 %.
# Basis: theta_v,mech = 18 °C; t_v,mech = 12 h; d_v,mech = 365 d.
VARIANTE_21_JAHR = {
    "qh_18C_12h": 1028.0,   # Wh/(m3/h)
    "gh_u": 227.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gh_o": 882.0,          # Wh/(K*m3/h), Zulufttemperatur 18-22°C
    "qc_18C_12h": 2443.0,   # Wh/(m3/h)
    "gc_u": 886.0,          # Wh/(K*m3/h), Zulufttemperatur 14-18°C
    "gc_o": 246.0,          # Wh/(K*m3/h), Zulufttemperatur 18-22°C
    "qst_18C_12h": 3992.0,  # Wh/(m3/h), Dampfbefeuchtung
}


@dataclass
class KennwertRandbedingungen:
    """Randbedingungen für die Anwendung des Kennwertverfahrens
    (Jahresverfahren, konstanter Volumenstrom) auf ein virtuelles
    Gebäude."""
    aussenluftvolumenstrom_m3h: float
    zulufttemperatur_soll_c: float  # theta_hc, 14..22 °C
    taegliche_betriebsstunden: float  # t_v,mech, 8..24 h
    jaehrliche_betriebstage: float  # d_v,mech, <= 365 d


def _fT_h(tv_mech: float) -> float:
    """Korrekturfaktor fT,h nach Gleichung (37), gültig für
    8 h <= tv_mech <= 24 h."""
    if not (8.0 <= tv_mech <= 24.0):
        raise ValueError("tv_mech muss im Bereich 8..24 h liegen (Gl. 37).")
    dt = tv_mech - 12.0
    return 1 + 6.125e-3 * dt - 2.813e-4 * dt**2 + 1.563e-5 * dt**3


def _fT_c_mit_toleranz(tv_mech: float) -> float:
    """Korrekturfaktor fT,c nach Gleichung (39) für Feuchteanforderungen
    "keine" oder "mit Toleranzbereich" (Variante 3), gültig für
    8 h <= tv_mech <= 24 h."""
    if not (8.0 <= tv_mech <= 24.0):
        raise ValueError("tv_mech muss im Bereich 8..24 h liegen (Gl. 39).")
    dt = tv_mech - 12.0
    return 1 - 1.561e-2 * dt - 8.479e-4 * dt**2 - 1.771e-5 * dt**3


def _qh_bei_zulufttemperatur(theta_hc: float, kennwerte: dict) -> float:
    """Umrechnung des Heizenergiekennwerts auf eine frei wählbare
    Zulufttemperatur nach Gleichung (29)/(30), gültig für
    14 °C <= theta_hc <= 22 °C."""
    if not (14.0 <= theta_hc <= 22.0):
        raise ValueError("theta_hc muss im Bereich 14..22 °C liegen (Gl. 26).")
    qh_18 = kennwerte["qh_18C_12h"]
    if theta_hc > 18.0:
        return qh_18 + kennwerte["gh_o"] * (theta_hc - 18.0)
    if theta_hc < 18.0:
        return qh_18 + kennwerte["gh_u"] * (theta_hc - 18.0)
    return qh_18


def _qc_bei_zulufttemperatur(theta_hc: float, kennwerte: dict) -> float:
    """Umrechnung des Kühlenergiekennwerts auf eine frei wählbare
    Zulufttemperatur nach Gleichung (31)/(32), gültig für
    14 °C <= theta_hc <= 22 °C. Beachte das Minuszeichen (im Unterschied
    zur Heizenergie sinkt der Kühlenergiebedarf mit zunehmendem Abstand
    des Zulufttemperatur-Sollwerts von 18 °C in beide Richtungen)."""
    if not (14.0 <= theta_hc <= 22.0):
        raise ValueError("theta_hc muss im Bereich 14..22 °C liegen (Gl. 26).")
    qc_18 = kennwerte["qc_18C_12h"]
    if theta_hc > 18.0:
        return qc_18 - kennwerte["gc_o"] * (theta_hc - 18.0)
    if theta_hc < 18.0:
        return qc_18 - kennwerte["gc_u"] * (theta_hc - 18.0)
    return qc_18


def jahres_heizenergiebedarf_kwh(
    randbedingungen: KennwertRandbedingungen,
    kennwerte: dict = VARIANTE_3_JAHR,
) -> float:
    """Jährlicher Nutzenergiebedarf Heizen (Luftaufbereitung) in kWh
    nach dem Kennwertverfahren der DIN V 18599-3, Jahresverfahren für
    Anlagen mit konstantem Volumenstrom (Abschnitt 4.4.1 i.V.m.
    Tabelle A.1).

    Berechnungsschritte:
    1. Umrechnung auf die gewählte Zulufttemperatur (Gl. 29/30).
    2. Umrechnung auf die tägliche Betriebszeit über fT,h (Gl. 34/37).
    3. Skalierung auf die tatsächliche Anzahl jährlicher Betriebstage
       (Tabelle A.1 basiert auf d_v,mech = 365 d).
    4. Denormierung auf den tatsächlichen Zuluftvolumenstrom (Gl. 42).
    """
    qh_theta = _qh_bei_zulufttemperatur(
        randbedingungen.zulufttemperatur_soll_c, kennwerte
    )
    fT_h = _fT_h(randbedingungen.taegliche_betriebsstunden)
    qh_stunden = qh_theta * (randbedingungen.taegliche_betriebsstunden / 12.0) * fT_h
    qh_tage = qh_stunden * (randbedingungen.jaehrliche_betriebstage / 365.0)
    q_h_wh = qh_tage * randbedingungen.aussenluftvolumenstrom_m3h
    return q_h_wh / 1000.0


def jahres_kaelteenergiebedarf_kwh(
    randbedingungen: KennwertRandbedingungen,
    kennwerte: dict = VARIANTE_3_JAHR,
) -> float:
    """Jährlicher Nutzenergiebedarf Kühlen (Luftaufbereitung) in kWh
    nach dem Kennwertverfahren der DIN V 18599-3, Jahresverfahren für
    Anlagen mit konstantem Volumenstrom (Abschnitt 4.4.1 i.V.m.
    Tabelle A.1), analog zu ``jahres_heizenergiebedarf_kwh`` mit dem
    Korrekturfaktor fT,c (Gl. 39, Gruppe "keine"/"mit Toleranzbereich").
    """
    qc_theta = _qc_bei_zulufttemperatur(
        randbedingungen.zulufttemperatur_soll_c, kennwerte
    )
    fT_c = _fT_c_mit_toleranz(randbedingungen.taegliche_betriebsstunden)
    qc_stunden = qc_theta * (randbedingungen.taegliche_betriebsstunden / 12.0) * fT_c
    qc_tage = qc_stunden * (randbedingungen.jaehrliche_betriebstage / 365.0)
    q_c_wh = qc_tage * randbedingungen.aussenluftvolumenstrom_m3h
    return q_c_wh / 1000.0


def jahres_dampfbefeuchtungsenergiebedarf_kwh(
    randbedingungen: KennwertRandbedingungen,
    kennwerte: dict = VARIANTE_21_JAHR,
) -> float:
    """Jährlicher Nutzenergiebedarf Dampfbefeuchtung in kWh nach dem
    Kennwertverfahren der DIN V 18599-3.

    Der Dampfenergiekennwert ist näherungsweise unabhängig von der
    Zulufttemperatur (Gl. 42 mit $f_{\\mathrm{T,st}} = 1{,}0$ konstant);
    lediglich die Skalierung auf die tägliche Betriebszeit, die
    tatsächliche Anzahl jährlicher Betriebstage sowie die Denormierung
    auf den Zuluftvolumenstrom erfolgen wie bei Heizen/Kühlen.
    """
    qst_theta = kennwerte["qst_18C_12h"]
    fT_st = 1.0
    qst_stunden = qst_theta * (randbedingungen.taegliche_betriebsstunden / 12.0) * fT_st
    qst_tage = qst_stunden * (randbedingungen.jaehrliche_betriebstage / 365.0)
    q_st_wh = qst_tage * randbedingungen.aussenluftvolumenstrom_m3h
    return q_st_wh / 1000.0
