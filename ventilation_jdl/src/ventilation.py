"""Ueberschlaegige, stuendliche Berechnung der Lueftungsenergiemengen.

Heiz- und Kuehlbilanz je Stunde des TRY-Jahres:

    Q_dot_h(t) = rho * c_p * V_dot_a(t) * delta_theta_h_eff(t)   (Heizfall)
    Q_dot_c(t) = rho * c_p * V_dot_a(t) * delta_theta_c_eff(t)   (Kuehlfall)

mit
    delta_theta_h_eff(t) = (1 - eta_WRG) * (theta_i - theta_e(t))   falls theta_e(t) < theta_i
    delta_theta_c_eff(t) = (1 - eta_WRG) * (theta_e(t) - theta_i,c) falls theta_e(t) > theta_i,c
    sonst jeweils 0

V_dot_a(t) wird nur waehrend der Betriebszeit des Gebaeudes angesetzt.

Fuer die Befeuchtung wird zusaetzlich eine latente Bilanz ueber die
spezifische Enthalpie feuchter Luft gebildet (CoolProp), fuer die
Ventilatoren eine einfache Leistungsberechnung ueber Druckerhoehung und
Wirkungsgrad.

Dies ist ein ueberschlaegiges Verfahren mit Stundenmittelwerten und ersetzt
nicht das Kennwertverfahren nach DIN V 18599-3.
"""

import datetime

import pandas as pd
from CoolProp.HumidAirProp import HAPropsSI

from weather import absolute_feuchte, luftdruck_pa

# Stoffwerte trockener Luft bei ca. 20 °C
RHO_LUFT = 1.20   # kg/m3
CP_LUFT = 1.005   # kJ/(kg*K)

# Referenzjahr (kein Schaltjahr), nur um aus Monat/Tag den Wochentag
# abzuleiten (TRY-Datensaetze gehoeren keinem realen Kalenderjahr an).
REFERENZJAHR = 2015


def _wochentag(monat, tag):
    return datetime.date(REFERENZJAHR, int(monat), int(tag)).weekday()


def betriebsmaske(wetter_df, gebaeude):
    """Gibt fuer jede Stunde True/False zurueck: ist das Gebaeude in Betrieb?"""
    wochentage = wetter_df.apply(lambda row: _wochentag(row["MM"], row["DD"]), axis=1)
    stunde_im_tag = wetter_df["HH"] % 24
    betrieb = [
        gebaeude.betriebszeit.ist_betrieb(wt, int(h))
        for wt, h in zip(wochentage, stunde_im_tag)
    ]
    return pd.Series(betrieb, index=wetter_df.index)


def heizleistung_kw(wetter_df, gebaeude):
    """Stuendliche Heizleistung der Lueftung in kW."""
    theta_e = wetter_df["t"]
    theta_i = gebaeude.solltemperatur_innen_c
    betrieb = betriebsmaske(wetter_df, gebaeude)

    delta_theta = (theta_i - theta_e).clip(lower=0.0)
    # delta_theta_eff = (1 - eta_WRG) * delta_theta ist die Umformung von
    # DIN V 18599-2:2018-09, Abschnitt 6.3.3.5, Gleichung (98):
    #   theta_v,mech = theta_e + eta_t * (theta_i - theta_e)
    # => theta_i - theta_v,mech = (1 - eta_t) * (theta_i - theta_e)
    # mit eta_t = waermerueckgewinnungsgrad (eta_WRG).
    delta_theta_eff = delta_theta * (1.0 - gebaeude.waermerueckgewinnungsgrad)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    leistung = RHO_LUFT * CP_LUFT * v_dot_m3s * delta_theta_eff

    return leistung.where(betrieb, other=0.0)


def kuehlleistung_kw(wetter_df, gebaeude):
    """Stuendliche Kuehlleistung der Lueftung in kW. 0, falls im Profil
    keine Kuehl-Solltemperatur hinterlegt ist."""
    if gebaeude.solltemperatur_kuehlung_c is None:
        return pd.Series(0.0, index=wetter_df.index)

    theta_e = wetter_df["t"]
    theta_i_c = gebaeude.solltemperatur_kuehlung_c
    betrieb = betriebsmaske(wetter_df, gebaeude)

    delta_theta = (theta_e - theta_i_c).clip(lower=0.0)
    delta_theta_eff = delta_theta * (1.0 - gebaeude.waermerueckgewinnungsgrad)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    leistung = RHO_LUFT * CP_LUFT * v_dot_m3s * delta_theta_eff

    return leistung.where(betrieb, other=0.0)


def befeuchtungsleistung_kw(wetter_df, gebaeude):
    """Stuendliche latente Befeuchtungsleistung in kW. 0, falls im Profil
    kein Feuchte-Sollwert der Zuluft hinterlegt ist.

    Q_dot_st(t) = m_dot_tL * (h(theta_i, x_soll) - h(theta_i, x_e(t)))

    h = spezifische Enthalpie feuchter Luft, berechnet mit CoolProp.
    """
    if gebaeude.feuchte_soll_gpkg is None:
        return pd.Series(0.0, index=wetter_df.index)

    theta_i = gebaeude.solltemperatur_innen_c
    x_e_gpkg = absolute_feuchte(wetter_df)
    p_pa = luftdruck_pa(wetter_df)
    x_soll_kgkg = gebaeude.feuchte_soll_gpkg / 1000.0
    betrieb = betriebsmaske(wetter_df, gebaeude)

    t_kelvin = theta_i + 273.15
    h_soll = HAPropsSI("Hha", "T", t_kelvin, "P", float(p_pa.mean()), "W", x_soll_kgkg)

    werte = []
    for x_gkg, p in zip(x_e_gpkg, p_pa):
        w = max(x_gkg, 0.0) / 1000.0
        h_aussen = HAPropsSI("Hha", "T", t_kelvin, "P", p, "W", w)
        werte.append(max(h_soll - h_aussen, 0.0))

    delta_h = pd.Series(werte, index=wetter_df.index)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    m_dot_kg_s = RHO_LUFT * v_dot_m3s
    leistung_kw = m_dot_kg_s * delta_h / 1000.0

    return leistung_kw.where(betrieb, other=0.0)


def ventilatorleistung_kw(wetter_df, gebaeude):
    """Stuendliche elektrische Ventilatorleistung (Zu- + Abluft) in kW.
    0, falls im Profil keine Druckerhoehungen bzw. kein Wirkungsgrad
    hinterlegt sind.

    P_V(t) = V_dot_a * (Delta_p_ZUL + Delta_p_ABL) / eta_V   waehrend Betrieb

    Dies ist der Sonderfall konstanten Volumenstroms (keine VAV-
    Teillastregelung) der Ventilatorleistung nach DIN V 18599-3.
    """
    hat_druck = gebaeude.druckerhoehung_zuluft_pa is not None or gebaeude.druckerhoehung_abluft_pa is not None
    if not hat_druck or gebaeude.wirkungsgrad_ventilator is None:
        return pd.Series(0.0, index=wetter_df.index)

    delta_p_pa = (gebaeude.druckerhoehung_zuluft_pa or 0.0) + (gebaeude.druckerhoehung_abluft_pa or 0.0)
    eta_v = gebaeude.wirkungsgrad_ventilator
    betrieb = betriebsmaske(wetter_df, gebaeude)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    leistung_w = v_dot_m3s * delta_p_pa / eta_v
    leistung_kw = pd.Series(leistung_w / 1000.0, index=wetter_df.index)

    return leistung_kw.where(betrieb, other=0.0)


def jahresenergiemenge_kwh(stuendliche_werte_kw):
    """Summe der stuendlichen Leistungswerte (kW) = Jahresenergiemenge (kWh)."""
    return float(stuendliche_werte_kw.sum())
