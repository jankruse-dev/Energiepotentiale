import pandas as pd
import pytest

from ventilation_jdl.building import Betriebszeit, VirtuellesGebaeude
from ventilation_jdl.ventilation import (
    jahresenergiemenge_kwh,
    stuendliche_befeuchtungsleistung_kw,
    stuendliche_kaelteleistung_kw,
)


def _synthetische_wetterdaten() -> pd.DataFrame:
    """Vier synthetische Stunden: kalt/trocken, warm/trocken,
    warm/feucht, warm/sehr-trocken – für gezielte Grenzfalltests."""
    return pd.DataFrame(
        {
            "MM": [1, 7, 7, 7],
            "DD": [1, 1, 1, 1],  # 1.1. (Mi) und 1.7. (Di), beide im Referenzjahr 2015 Werktage
            "HH": [12, 12, 13, 14],
            "t": [-5.0, 30.0, 30.0, 30.0],
            "x": [3.0, 12.0, 12.0, 2.0],
            "p": [1013.0, 1013.0, 1013.0, 1013.0],
        },
        index=pd.RangeIndex(1, 5, name="stunde_des_jahres"),
    )


def _gebaeude(**overrides) -> VirtuellesGebaeude:
    basis = dict(
        name="Test",
        nutzungsprofil="Test",
        aussenluftvolumenstrom_m3h=1000.0,
        solltemperatur_innen_c=21.0,
        betriebszeit=Betriebszeit(start_stunde=0, end_stunde=24, wochentage=(0, 1, 2, 3, 4, 5, 6)),
        waermerueckgewinnungsgrad=0.0,
    )
    basis.update(overrides)
    return VirtuellesGebaeude(**basis)


def test_kaelteleistung_ohne_kuehl_sollwert_ist_null():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=None)
    kaelte = stuendliche_kaelteleistung_kw(weather_df, gebaeude)
    assert (kaelte == 0.0).all()


def test_kaelteleistung_bei_warmer_aussenluft_positiv():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=24.0)
    kaelte = stuendliche_kaelteleistung_kw(weather_df, gebaeude)
    # Stunde 1 (t=-5°C, unter Kühl-Sollwert): kein Kühlfall
    assert kaelte.iloc[0] == 0.0
    # Stunden 2-4 (t=30°C > 24°C): Kühlfall aktiv
    assert (kaelte.iloc[1:] > 0.0).all()


def test_befeuchtungsleistung_ohne_soll_ist_null():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(feuchte_soll_gpkg=None)
    befeuchtung = stuendliche_befeuchtungsleistung_kw(weather_df, gebaeude)
    assert (befeuchtung == 0.0).all()


def test_befeuchtungsleistung_nur_bei_trockener_aussenluft():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(feuchte_soll_gpkg=6.0)
    befeuchtung = stuendliche_befeuchtungsleistung_kw(weather_df, gebaeude)
    # Stunden mit x=12 g/kg (> Soll 6 g/kg): keine Befeuchtung noetig
    assert befeuchtung.iloc[1] == pytest.approx(0.0, abs=1e-9)
    assert befeuchtung.iloc[2] == pytest.approx(0.0, abs=1e-9)
    # Stunde mit x=2 g/kg (< Soll 6 g/kg): Befeuchtung aktiv
    assert befeuchtung.iloc[3] > 0.0
    # Stunde mit x=3 g/kg (< Soll 6 g/kg): Befeuchtung aktiv
    assert befeuchtung.iloc[0] > 0.0


def test_jahresenergiemenge_summiert_kaelte_korrekt():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=24.0)
    kaelte = stuendliche_kaelteleistung_kw(weather_df, gebaeude)
    summe = jahresenergiemenge_kwh(kaelte)
    assert summe == pytest.approx(float(kaelte.sum()))
