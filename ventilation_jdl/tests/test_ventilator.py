import pandas as pd
import pytest

from ventilation_jdl.building import Betriebszeit, VirtuellesGebaeude
from ventilation_jdl.ventilation import (
    jahresenergiemenge_kwh,
    stuendliche_ventilatorleistung_kw,
)


def _synthetische_wetterdaten() -> pd.DataFrame:
    """Drei synthetische Stunden im Betrieb, eine außerhalb der
    Betriebszeit – die Ventilatorleistung hängt nicht von der
    Außentemperatur ab, sondern nur vom Betriebszustand."""
    return pd.DataFrame(
        {
            "MM": [1, 1, 1, 1],
            "DD": [1, 1, 1, 1],  # 1.1. (Do) im Referenzjahr 2015, Werktag
            "HH": [6, 12, 18, 23],
            "t": [-5.0, 5.0, 2.0, -8.0],
            "x": [3.0, 4.0, 3.5, 2.0],
            "p": [1013.0, 1013.0, 1013.0, 1013.0],
        },
        index=pd.RangeIndex(1, 5, name="stunde_des_jahres"),
    )


def _gebaeude(**overrides) -> VirtuellesGebaeude:
    basis = dict(
        name="Test",
        nutzungsprofil="Test",
        aussenluftvolumenstrom_m3h=3600.0,  # 1 m3/s, praktisch für die Kontrollrechnung
        solltemperatur_innen_c=21.0,
        betriebszeit=Betriebszeit(start_stunde=7, end_stunde=19, wochentage=(0, 1, 2, 3, 4, 5, 6)),
        waermerueckgewinnungsgrad=0.0,
    )
    basis.update(overrides)
    return VirtuellesGebaeude(**basis)


def test_ventilatorleistung_ohne_parameter_ist_null():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(
        druckerhoehung_zuluft_pa=None,
        druckerhoehung_abluft_pa=None,
        wirkungsgrad_ventilator=None,
    )
    leistung = stuendliche_ventilatorleistung_kw(weather_df, gebaeude)
    assert (leistung == 0.0).all()


def test_ventilatorleistung_ohne_wirkungsgrad_ist_null():
    """Ohne hinterlegten Wirkungsgrad kann keine Leistung berechnet werden,
    auch wenn Druckerhöhungen vorliegen."""
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(
        druckerhoehung_zuluft_pa=300.0,
        druckerhoehung_abluft_pa=250.0,
        wirkungsgrad_ventilator=None,
    )
    leistung = stuendliche_ventilatorleistung_kw(weather_df, gebaeude)
    assert (leistung == 0.0).all()


def test_ventilatorleistung_nur_waehrend_betriebszeit():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(
        druckerhoehung_zuluft_pa=300.0,
        druckerhoehung_abluft_pa=250.0,
        wirkungsgrad_ventilator=0.6,
    )
    leistung = stuendliche_ventilatorleistung_kw(weather_df, gebaeude)
    # Stunden 12 und 18 Uhr liegen innerhalb 7-19 Uhr, 6 und 23 Uhr außerhalb
    assert leistung.iloc[0] == 0.0  # 6 Uhr
    assert leistung.iloc[1] > 0.0  # 12 Uhr
    assert leistung.iloc[2] > 0.0  # 18 Uhr
    assert leistung.iloc[3] == 0.0  # 23 Uhr


def test_ventilatorleistung_formel_p_gleich_v_dot_mal_dp_durch_eta():
    """Kontrollrechnung: V_dot=1 m3/s, Delta_p=550 Pa, eta=0.55
    => P = 1 * 550 / 0.55 = 1000 W = 1 kW."""
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(
        aussenluftvolumenstrom_m3h=3600.0,
        druckerhoehung_zuluft_pa=300.0,
        druckerhoehung_abluft_pa=250.0,
        wirkungsgrad_ventilator=0.55,
    )
    leistung = stuendliche_ventilatorleistung_kw(weather_df, gebaeude)
    assert leistung.iloc[1] == pytest.approx(1.0, rel=1e-9)


def test_jahresenergiemenge_summiert_ventilatorleistung_korrekt():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(
        druckerhoehung_zuluft_pa=300.0,
        druckerhoehung_abluft_pa=250.0,
        wirkungsgrad_ventilator=0.6,
    )
    leistung = stuendliche_ventilatorleistung_kw(weather_df, gebaeude)
    summe = jahresenergiemenge_kwh(leistung)
    assert summe == pytest.approx(float(leistung.sum()))
