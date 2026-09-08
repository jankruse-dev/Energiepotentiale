"""Überschlägige, stündliche Berechnung der Lüftungsenergiemengen.

Die sensible Heiz- und Kühlbilanz erfolgt als direkte Energiebilanz je
Stunde des TRY-Jahres:

    Q_dot_h(t) = rho * c_p * V_dot_a(t) * delta_theta_h_eff(t)   (Heizfall)
    Q_dot_c(t) = rho * c_p * V_dot_a(t) * delta_theta_c_eff(t)   (Kühlfall)

mit

    delta_theta_h_eff(t) = (1 - eta_WRG) * (theta_i - theta_e(t))   falls theta_e(t) < theta_i
    delta_theta_c_eff(t) = (1 - eta_WRG) * (theta_e(t) - theta_i,c) falls theta_e(t) > theta_i,c
    sonst jeweils 0 (kein Heiz- bzw. Kühlfall)

V_dot_a(t) ist der Außenluftvolumenstrom, der nur während der Betriebszeit
des Gebäudes ungleich null angesetzt wird. Der Kühlfall wird nur berechnet,
wenn im Gebäudeprofil eine Kühl-Solltemperatur hinterlegt ist.

Für den Kühlfall kann zusätzlich die latente Kondensation am Luftkühler
berücksichtigt werden (siehe ``stuendliche_kaelteleistung_gesamt_kw`` und
``stuendliche_latente_kuehlleistung_kw``), nach dem Komponentenmodell
"Luftkühler" der DIN V 18599-3, Anhang C (Gl. C.3/C.4): Kondensation
tritt auf, sobald die relative Feuchte an der Kühler-Austrittsisotherme
95 % überschreiten würde; die Zuluft folgt dann der Isohygre phi = 0,95
statt der Isothermen bei konstantem x.

Für die Luftbefeuchtung wird zusätzlich eine latente Bilanz auf Basis der
spezifischen Enthalpie feuchter Luft gebildet (siehe
``stuendliche_befeuchtungsleistung_kw``), sofern im Gebäudeprofil ein
Mindest-Wasserdampfgehalt der Zuluft vorgegeben ist.

Zusätzlich kann die elektrische Jahresenergiemenge der Zu- und
Abluftventilatoren berechnet werden (siehe
``stuendliche_ventilatorleistung_kw``), sofern im Gebäudeprofil
Druckerhöhungen und ein Ventilatorwirkungsgrad hinterlegt sind:

    P_V(t) = V_dot_a * (Delta_p_ZUL + Delta_p_ABL) / eta_V

als Sonderfall (konstanter Volumenstrom, keine VAV-Teillastregelung) der
allgemeinen Ventilatorleistung nach DIN V 18599-3, Gleichungen (15)/(16).

Dies ist ein überschlägiges Verfahren mit Stundenmittelwerten und ersetzt
nicht das detaillierte Kennwertverfahren nach DIN V 18599-3, Abschnitt
4.4.1 (Normierung auf Referenzbedingungen, monatliche Korrekturfaktoren).
"""

from __future__ import annotations

import datetime as _dt

import numpy as np
import pandas as pd
from CoolProp.HumidAirProp import HAPropsSI

from building import Gebaeude
from weather import absolute_humidity, air_pressure_pa

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


def berechne_betriebsmaske(weather_df: pd.DataFrame, gebaeude: Gebaeude) -> pd.Series:
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
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündlicher Lüftungswärmeverlust (Heizfall) in kW über das TRY-Jahr."""
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


def stuendliche_kaelteleistung_kw(
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündlicher Lüftungskälteverlust (Kühlfall) in kW über das
    TRY-Jahr. Liefert eine Nullreihe, wenn im Gebäudeprofil keine
    Kühl-Solltemperatur hinterlegt ist (kein Kühlfall vorgesehen)."""
    if gebaeude.solltemperatur_kuehlung_c is None:
        return pd.Series(0.0, index=weather_df.index, name="kaelteleistung_kw")

    theta_e = weather_df["t"]
    theta_i_c = gebaeude.solltemperatur_kuehlung_c
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    delta_theta = (theta_e - theta_i_c).clip(lower=0.0)
    delta_theta_eff = delta_theta * (1.0 - gebaeude.waermerueckgewinnungsgrad)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    q_dot_kw = RHO_LUFT * CP_LUFT * v_dot_m3s * delta_theta_eff  # kJ/s = kW

    q_dot_kw = q_dot_kw.where(betrieb, other=0.0)
    q_dot_kw.name = "kaelteleistung_kw"
    return q_dot_kw


def stuendliche_kaelteleistung_gesamt_kw(
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündliche Kälteleistung am Luftkühler (sensibel + latent) in kW
    über das TRY-Jahr, nach dem Komponentenmodell "Luftkühler" der
    DIN V 18599-3, Anhang C (normativ), Gleichungen (C.3)/(C.4).

    Liefert eine Nullreihe, wenn im Gebäudeprofil keine
    Kühl-Solltemperatur hinterlegt ist.

    Nach Anhang C wird die Richtung der Zustandsänderung am Kühler über
    die relative Feuchte phi_L geprüft, die sich einstellen würde, wenn
    die Luft bei unverändertem Wasserdampfgehalt x auf die
    Kühler-Austrittstemperatur (hier: Kühl-Solltemperatur theta_i,c)
    gebracht würde:

    - phi_L <= 0,95: reine sensible Kühlung (Delta x = 0). In diesem
      Fall stimmt das Ergebnis mit ``stuendliche_kaelteleistung_kw``
      überein.
    - phi_L > 0,95: es tritt Kondensation am Kühler auf. Der
      Zuluftzustand ergibt sich als Schnittpunkt der Isotherme
      theta_i,c mit der Isohygre phi_L = 0,95 (praxisnahe Näherung an
      die Sättigungslinie, berücksichtigt den realen "Bypass-Faktor"
      des Kühlers). Die Kälteleistung folgt dann aus der
      Enthalpiedifferenz zwischen Kühler-Eintritt und Kühler-Austritt:

        Q_dot_c(t) = m_dot_tL * (h(theta_coil,in(t), x_e(t))
                                  - h(theta_i,c, x_out(t)))

    Die Kühler-Eintrittstemperatur theta_coil,in(t) berücksichtigt die
    Vorkühlung der Außenluft durch die Wärmerückgewinnung (ohne
    Feuchteübertragung, siehe Notiz zur treibenden Temperaturdifferenz)
    und entspricht der bereits in ``stuendliche_kaelteleistung_kw``
    verwendeten effektiven Temperatur theta_i,c + delta_theta_c_eff(t).
    Der Wasserdampfgehalt der Außenluft x_e(t) bleibt durch die WRG
    unverändert.
    """
    if gebaeude.solltemperatur_kuehlung_c is None:
        return pd.Series(0.0, index=weather_df.index, name="kaelteleistung_gesamt_kw")

    theta_e = weather_df["t"]
    theta_i_c = gebaeude.solltemperatur_kuehlung_c
    x_e_gpkg = absolute_humidity(weather_df)
    p_pa = air_pressure_pa(weather_df)
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    delta_theta = (theta_e - theta_i_c).clip(lower=0.0)
    delta_theta_eff = delta_theta * (1.0 - gebaeude.waermerueckgewinnungsgrad)
    theta_coil_in = theta_i_c + delta_theta_eff

    t_ic_kelvin = theta_i_c + 273.15

    def _q_dot_stunde(theta_ein: float, x_gkg: float, p: float, im_kuehlfall: bool) -> float:
        if not im_kuehlfall:
            return 0.0
        w_e = max(x_gkg, 0.0) / 1000.0
        try:
            phi_check = HAPropsSI("RH", "T", t_ic_kelvin, "P", p, "W", w_e)
            kondensiert = phi_check > 0.95
        except ValueError:
            # CoolProp meldet einen Wertebereichsfehler, wenn die
            # rechnerische relative Feuchte bei unveraendertem x oberhalb
            # von 100 % (uebersaettigt) liegen wuerde - das bedeutet
            # zweifelsfrei phi_L > 0,95, also Kondensation.
            kondensiert = True
        if kondensiert:
            w_out = HAPropsSI("W", "T", t_ic_kelvin, "P", p, "RH", 0.95)
        else:
            w_out = w_e
        t_ein_kelvin = theta_ein + 273.15
        h_ein = HAPropsSI("Hha", "T", t_ein_kelvin, "P", p, "W", w_e)
        h_aus = HAPropsSI("Hha", "T", t_ic_kelvin, "P", p, "W", w_out)
        delta_h_j_pro_kg = max(h_ein - h_aus, 0.0)
        return delta_h_j_pro_kg

    im_kuehlfall = delta_theta > 0.0
    delta_h_j_pro_kg = pd.Series(
        [
            _q_dot_stunde(te, x, p, kf)
            for te, x, p, kf in zip(theta_coil_in, x_e_gpkg, p_pa, im_kuehlfall)
        ],
        index=weather_df.index,
    )

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    m_dot_kg_s = RHO_LUFT * v_dot_m3s
    q_dot_kw = m_dot_kg_s * delta_h_j_pro_kg / 1000.0  # W -> kW

    q_dot_kw = q_dot_kw.where(betrieb, other=0.0)
    q_dot_kw.name = "kaelteleistung_gesamt_kw"
    return q_dot_kw


def stuendliche_latente_kuehlleistung_kw(
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündlicher latenter Anteil der Kälteleistung am Luftkühler in kW
    (Kondensationsanteil nach DIN V 18599-3, Anhang C, Gl. C.3/C.4).

    Der latente Anteil wird als Enthalpiedifferenz durch die
    Entfeuchtung bei konstanter Kühler-Austrittstemperatur theta_i,c
    gebildet (Differenz des Wasserdampfgehalts x_e(t) vor und x_out(t)
    nach der Kondensation an der Isohygre phi = 0,95):

        Q_dot_st(t) = m_dot_tL * (h(theta_i,c, x_e(t)) - h(theta_i,c, x_out(t)))

    Er ist bewusst NICHT als Differenz aus Gesamt- und Sensibelanteil
    gebildet, da diese Differenz auch die kleine Abweichung zwischen der
    vereinfachten Sensibelrechnung (konstantes c_p trockener Luft in
    ``stuendliche_kaelteleistung_kw``) und der exakten Enthalpie
    feuchter Luft enthalten würde. In Stunden ohne Kondensation
    (phi_L <= 0,95 an der Kühler-Austrittsisotherme) ist dieser Anteil
    exakt null.
    """
    if gebaeude.solltemperatur_kuehlung_c is None:
        return pd.Series(0.0, index=weather_df.index, name="latente_kuehlleistung_kw")

    theta_e = weather_df["t"]
    theta_i_c = gebaeude.solltemperatur_kuehlung_c
    x_e_gpkg = absolute_humidity(weather_df)
    p_pa = air_pressure_pa(weather_df)
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    delta_theta = (theta_e - theta_i_c).clip(lower=0.0)
    t_ic_kelvin = theta_i_c + 273.15

    def _q_dot_latent_stunde(x_gkg: float, p: float, im_kuehlfall: bool) -> float:
        if not im_kuehlfall:
            return 0.0
        w_e = max(x_gkg, 0.0) / 1000.0
        try:
            phi_check = HAPropsSI("RH", "T", t_ic_kelvin, "P", p, "W", w_e)
            kondensiert = phi_check > 0.95
        except ValueError:
            kondensiert = True
        if not kondensiert:
            return 0.0
        w_out = HAPropsSI("W", "T", t_ic_kelvin, "P", p, "RH", 0.95)
        h_e = HAPropsSI("Hha", "T", t_ic_kelvin, "P", p, "W", w_e)
        h_out = HAPropsSI("Hha", "T", t_ic_kelvin, "P", p, "W", w_out)
        return max(h_e - h_out, 0.0)

    im_kuehlfall = delta_theta > 0.0
    delta_h_j_pro_kg = pd.Series(
        [
            _q_dot_latent_stunde(x, p, kf)
            for x, p, kf in zip(x_e_gpkg, p_pa, im_kuehlfall)
        ],
        index=weather_df.index,
    )

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    m_dot_kg_s = RHO_LUFT * v_dot_m3s
    q_dot_kw = m_dot_kg_s * delta_h_j_pro_kg / 1000.0  # W -> kW

    q_dot_kw = q_dot_kw.where(betrieb, other=0.0)
    q_dot_kw.name = "latente_kuehlleistung_kw"
    return q_dot_kw


def stuendliche_befeuchtungsleistung_kw(
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündliche Befeuchtungsleistung (latenter Anteil) in kW über das
    TRY-Jahr. Liefert eine Nullreihe, wenn im Gebäudeprofil kein
    Mindest-Wasserdampfgehalt der Zuluft hinterlegt ist (keine
    Befeuchtung vorgesehen).

    Die latente Leistung wird als Differenz der spezifischen Enthalpie
    feuchter Luft bei konstanter Zulufttemperatur (Raum-Solltemperatur)
    zwischen dem Zustand der Außenluft und dem geforderten
    Mindest-Wasserdampfgehalt gebildet:

        Q_dot_st(t) = m_dot_tL * (h(theta_i, x_soll) - h(theta_i, x_e(t)))

    mit h = spezifische Enthalpie feuchter Luft je kg trockener Luft
    (berechnet mit CoolProp/HumidAirProp). Dies erfasst sowohl den
    latenten Anteil (Verdampfungsenthalpie des zugeführten Wassers) als
    auch den kleinen sensiblen Anteil durch das Aufheizen des
    zugeführten Wasserdampfs auf Zulufttemperatur.
    """
    if gebaeude.feuchte_soll_gpkg is None:
        return pd.Series(0.0, index=weather_df.index, name="befeuchtungsleistung_kw")

    theta_i = gebaeude.solltemperatur_innen_c
    x_e_gpkg = absolute_humidity(weather_df)
    p_pa = air_pressure_pa(weather_df)
    x_soll_kgkg = gebaeude.feuchte_soll_gpkg / 1000.0
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    t_kelvin = theta_i + 273.15
    h_soll = HAPropsSI("Hha", "T", t_kelvin, "P", float(p_pa.mean()), "W", x_soll_kgkg)

    def _h_aussen(x_gkg: float, p: float) -> float:
        w = max(x_gkg, 0.0) / 1000.0
        return HAPropsSI("Hha", "T", t_kelvin, "P", p, "W", w)

    h_aussen = pd.Series(
        [_h_aussen(x, p) for x, p in zip(x_e_gpkg, p_pa)],
        index=weather_df.index,
    )

    delta_h_j_pro_kg = (h_soll - h_aussen).clip(lower=0.0)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    m_dot_kg_s = RHO_LUFT * v_dot_m3s
    q_dot_kw = m_dot_kg_s * delta_h_j_pro_kg / 1000.0  # W -> kW

    q_dot_kw = q_dot_kw.where(betrieb, other=0.0)
    q_dot_kw.name = "befeuchtungsleistung_kw"
    return q_dot_kw


def stuendliche_ventilatorleistung_kw(
    weather_df: pd.DataFrame, gebaeude: Gebaeude
) -> pd.Series:
    """Stündliche elektrische Ventilatorleistung (Zu- und Abluft) in kW
    über das TRY-Jahr. Liefert eine Nullreihe, wenn im Gebäudeprofil
    keine Druckerhöhungen bzw. kein Ventilatorwirkungsgrad hinterlegt
    sind (keine Ventilatorberechnung vorgesehen).

    Berechnungsgrundlage ist die Ventilatorleistung nach DIN V 18599-3,
    Gleichungen (15)/(16):

        P_V = V_dot * fp * Delta_p / eta_V

    mit fp = Druckverhältnis-Zahl (Verhältnis von aktuellem zu
    Auslegungs-Volumenstrom bei Teillast, siehe DIN V 18599-3). Für die
    hier betrachteten Anlagen mit konstantem Volumenstrom (keine
    Volumenstromregelung/VAV, V_dot = V_dot* während der gesamten
    Betriebszeit) reduziert sich dies auf den einfachen Sonderfall
    fp = 1:

        P_V(t) = V_dot_a * (Delta_p_ZUL + Delta_p_ABL) / eta_V   während Betrieb, sonst 0

    Die Jahresenergiemenge ergibt sich analog zu DIN V 18599-3,
    Gleichung (25) (dort monatsweise: W_V,mth = t_V,mech,mth * (P_V,SUP +
    P_V,ETA)) durch Summation über die Betriebsstunden des Jahres. Der
    Ventilatorwirkungsgrad eta_V nach DIN V 18599-7, Abschnitt 3.1.2
    (SFP-Wert: spezifische elektrische Leistungsaufnahme je
    Volumenstrom) fasst dabei Ventilator-, Motor- und ggf.
    Antriebswirkungsgrad zusammen.
    """
    if (
        gebaeude.druckerhoehung_zuluft_pa is None
        and gebaeude.druckerhoehung_abluft_pa is None
    ) or gebaeude.wirkungsgrad_ventilator is None:
        return pd.Series(0.0, index=weather_df.index, name="ventilatorleistung_kw")

    delta_p_pa = (gebaeude.druckerhoehung_zuluft_pa or 0.0) + (
        gebaeude.druckerhoehung_abluft_pa or 0.0
    )
    eta_v = gebaeude.wirkungsgrad_ventilator
    betrieb = berechne_betriebsmaske(weather_df, gebaeude)

    v_dot_m3s = gebaeude.aussenluftvolumenstrom_m3h / 3600.0
    p_v_w = v_dot_m3s * delta_p_pa / eta_v  # W (m3/s * Pa = W)
    p_v_kw = p_v_w / 1000.0

    p_v_kw = pd.Series(p_v_kw, index=weather_df.index).where(betrieb, other=0.0)
    p_v_kw.name = "ventilatorleistung_kw"
    return p_v_kw


def jahresenergiemenge_kwh(stuendlich_kw: pd.Series) -> float:
    """Summiert die stündlichen Leistungswerte (kW) zur Jahresenergiemenge
    (kWh). Da die zeitliche Auflösung 1 h beträgt, entspricht die Summe
    der kW-Werte direkt der Energiemenge in kWh.
    """
    return float(stuendlich_kw.sum())
