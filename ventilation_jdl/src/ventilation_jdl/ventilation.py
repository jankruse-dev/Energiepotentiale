"""Überschlägige, stündliche Berechnung des Lüftungswärmeverlusts.

Die Berechnung erfolgt als direkte Energiebilanz je Stunde des TRY-Jahres:

    Q_dot_V(t) = rho * c_p * V_dot_a(t) * delta_theta_eff(t)

mit

    delta_theta_eff(t) = (1 - eta_WRG) * (theta_i - theta_e(t))   falls theta_e(t) < theta_i
    delta_theta_eff(t) = 0                                        sonst (kein Heizfall)

V_dot_a(t) ist der Außenluftvolumenstrom, der nur während der Betriebszeit
des Gebäudes ungleich null angesetzt wird.

Dies ist ein überschlägiges Verfahren mit Stundenmittelwerten und ersetzt
nicht das detaillierte Kennwertverfahren nach DIN V 18599-3, Abschnitt
4.4.1 (Normierung auf Referenzbedingungen, monatliche Korrekturfaktoren).
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd

from .building import VirtuellesGebaeude

# Stoffwerte trockener Luft bei ca. 20 °C (Näherungswerte)
RHO_LUFT = 1.20  # kg/m3
CP_LUFT = 1.005  # kJ/(kg*K)

# Referenzjahr (kein Schaltjahr) ausschließlich zur Ableitung des
# Wochentags aus Monat/Tag der TRY-Datei, da TRY-Datensätze keinem
# realen Kalenderjahr zugeordnet sind.
REFERENZJAHR = 2015


def _wochentag(monat: int, tag: int) -> int:
    """Wochentag (0 = Montag .. 6 = Sonntag) im Referenzjahr."""
    return _dt.date(REFERENZJAHR, int(monat), int(tag)).weekday()


def berechne_betriebsmaske(weather_df: pd.DataFrame, gebaeude: VirtuellesGebaeude) -> pd.Series:
    """Bestimmt für jede Stunde des TRY-Jahres, ob sich das Gebäude im
    Betrieb befindet (True/False), auf Basis der hinterlegten
    Betriebszeit.
    """
    wochentage = weather_df.apply(
        lambda row: _wochentag(row["MM"], row["DD"]), axis=1
    )
    stunde_im_tag = weather_df["HH"] % 24
    betrieb = [
        gebaeude.betriebszeit.ist_betrieb(wt, int(h))
        for wt, h in zip(wochentage, stunde_im_tag)
    ]
    return pd.Series(betrieb, index=weather_df.index, name="betrieb")


def stuendlicher_waermeverlust_kw(
    weather_df: pd.DataFrame, gebaeude: VirtuellesGebaeude
) -> pd.Series:
    """Stündlicher Lüftungswärmeverlust in kW über das TRY-Jahr."""
    theta_e = weather_df["t"]
    theta_i = gebaeude.solltemperatur_innen_c
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    delta_theta = (theta_i - theta_e).clip(lower=0.0)
    delta_theta_eff = delta_theta * (1.0 - gebaeude.waermerueckgewinnungsgrad)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    q_dot_kw = RHO_LUFT * CP_LUFT * v_dot_m3s * delta_theta_eff  # kJ/s = kW

    q_dot_kw = q_dot_kw.where(betrieb, other=0.0)
    q_dot_kw.name = "waermeverlust_kw"
    return q_dot_kw


def jahresenergiemenge_kwh(stuendlich_kw: pd.Series) -> float:
    """Summiert die stündlichen Leistungswerte (kW) zur Jahresenergiemenge
    (kWh). Da die zeitliche Auflösung 1 h beträgt, entspricht die Summe
    der kW-Werte direkt der Energiemenge in kWh.
    """
    return float(stuendlich_kw.sum())
