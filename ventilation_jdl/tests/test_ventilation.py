import pandas as pd

from ventilation_jdl.building import Betriebszeit, VirtuellesGebaeude
from ventilation_jdl.ventilation import (
    berechne_betriebsmaske,
    jahresenergiemenge_kwh,
    stuendlicher_waermeverlust_kw,
)


def _dummy_weather_df() -> pd.DataFrame:
    """Erzeugt einen minimalen, synthetischen Jahresdatensatz (kein
    echtes TRY, nur zum Testen der Berechnungslogik).
    """
    rows = []
    for monat in range(1, 13):
        tage_im_monat = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                          7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[monat]
        for tag in range(1, tage_im_monat + 1):
            for stunde in range(1, 25):
                rows.append({"MM": monat, "DD": tag, "HH": stunde, "t": 5.0})
    df = pd.DataFrame(rows)
    df.index = pd.RangeIndex(1, len(df) + 1, name="stunde_des_jahres")
    return df


def _beispielgebaeude(wrg: float = 0.0) -> VirtuellesGebaeude:
    return VirtuellesGebaeude(
        name="Test",
        nutzungsprofil="Einzelbüro",
        aussenluftvolumenstrom_m3h=3600.0,  # 1 m3/s
        solltemperatur_innen_c=20.0,
        betriebszeit=Betriebszeit(start_stunde=0, end_stunde=24, wochentage=(0, 1, 2, 3, 4, 5, 6)),
        waermerueckgewinnungsgrad=wrg,
    )


def test_betriebsmaske_ganztags_immer_true():
    df = _dummy_weather_df()
    gebaeude = _beispielgebaeude()
    maske = berechne_betriebsmaske(df, gebaeude)
    assert maske.all()


def test_waermeverlust_ohne_wrg():
    df = _dummy_weather_df()
    gebaeude = _beispielgebaeude(wrg=0.0)
    q_dot = stuendlicher_waermeverlust_kw(df, gebaeude)
    # delta_theta = 20 - 5 = 15 K, V_dot = 1 m3/s -> Q_dot = rho*cp*V_dot*dT
    erwartet = 1.20 * 1.005 * 1.0 * 15.0
    assert abs(q_dot.iloc[0] - erwartet) < 1e-6


def test_waermerueckgewinnung_reduziert_verlust():
    df = _dummy_weather_df()
    ohne_wrg = stuendlicher_waermeverlust_kw(df, _beispielgebaeude(wrg=0.0))
    mit_wrg = stuendlicher_waermeverlust_kw(df, _beispielgebaeude(wrg=0.6))
    assert (mit_wrg <= ohne_wrg).all()
    assert abs(mit_wrg.iloc[0] - 0.4 * ohne_wrg.iloc[0]) < 1e-6


def test_jahresenergiemenge_positiv():
    df = _dummy_weather_df()
    gebaeude = _beispielgebaeude()
    q_dot = stuendlicher_waermeverlust_kw(df, gebaeude)
    q_jahr = jahresenergiemenge_kwh(q_dot)
    assert q_jahr > 0


def test_keine_heizlast_bei_aussentemperatur_ueber_soll():
    df = _dummy_weather_df()
    df["t"] = 25.0  # wärmer als Solltemperatur
    gebaeude = _beispielgebaeude()
    q_dot = stuendlicher_waermeverlust_kw(df, gebaeude)
    assert (q_dot == 0).all()
