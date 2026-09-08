import pandas as pd
import pytest

from ventilation_jdl.building import Betriebszeit, VirtuellesGebaeude
from ventilation_jdl.ventilation import (
    jahresenergiemenge_kwh,
    stuendliche_befeuchtungsleistung_kw,
    stuendliche_kaelteleistung_gesamt_kw,
    stuendliche_kaelteleistung_kw,
    stuendliche_latente_kuehlleistung_kw,
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


def _synthetische_wetterdaten_kondensation() -> pd.DataFrame:
    """Vier synthetische Stunden zur gezielten Prüfung des
    Luftkühler-Kondensationsmodells (Anhang C, Gl. C.3/C.4): kalt,
    warm/sehr feucht (2x, oberhalb der 95-%-Isohygre bei 24°C), warm/
    trocken (keine Kondensation)."""
    return pd.DataFrame(
        {
            "MM": [1, 7, 7, 7],
            "DD": [1, 1, 1, 1],
            "HH": [12, 12, 13, 14],
            "t": [-5.0, 32.0, 32.0, 32.0],
            "x": [3.0, 20.0, 20.0, 2.0],
            "p": [1013.0, 1013.0, 1013.0, 1013.0],
        },
        index=pd.RangeIndex(1, 5, name="stunde_des_jahres"),
    )


def test_kaelteleistung_gesamt_ohne_kuehl_sollwert_ist_null():
    weather_df = _synthetische_wetterdaten_kondensation()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=None)
    gesamt = stuendliche_kaelteleistung_gesamt_kw(weather_df, gebaeude)
    latent = stuendliche_latente_kuehlleistung_kw(weather_df, gebaeude)
    assert (gesamt == 0.0).all()
    assert (latent == 0.0).all()


def test_kaelteleistung_gesamt_entspricht_sensibel_ohne_kondensation():
    """Warme, aber trockene Außenluft (Stunde 4, x=2 g/kg): die
    rechnerische relative Feuchte am Kühlerausgang bleibt <= 95 %, daher
    keine Kondensation - latenter Anteil muss exakt null sein."""
    weather_df = _synthetische_wetterdaten_kondensation()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=24.0)
    latent = stuendliche_latente_kuehlleistung_kw(weather_df, gebaeude)
    assert latent.iloc[3] == pytest.approx(0.0, abs=1e-9)


def test_kaelteleistung_gesamt_groesser_bei_kondensation():
    """Warme UND sehr feuchte Außenluft (Stunden 2-3, x=20 g/kg): die
    rechnerische relative Feuchte am Kühlerausgang überschreitet 95 %,
    daher Kondensation entlang der Isohygre phi=0,95 - die
    Gesamtkälteleistung muss die sensible Kälteleistung übersteigen und
    der latente Anteil muss positiv sein."""
    weather_df = _synthetische_wetterdaten_kondensation()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=24.0)
    sensibel = stuendliche_kaelteleistung_kw(weather_df, gebaeude)
    gesamt = stuendliche_kaelteleistung_gesamt_kw(weather_df, gebaeude)
    latent = stuendliche_latente_kuehlleistung_kw(weather_df, gebaeude)

    assert gesamt.iloc[1] == pytest.approx(4.3519, rel=0.01)
    assert gesamt.iloc[1] > sensibel.iloc[1]
    assert latent.iloc[1] == pytest.approx(1.6216, rel=0.01)
    assert latent.iloc[1] == latent.iloc[2]  # gleiche Randbedingungen


def test_jahresenergiemenge_summiert_kaelte_korrekt():
    weather_df = _synthetische_wetterdaten()
    gebaeude = _gebaeude(solltemperatur_kuehlung_c=24.0)
    kaelte = stuendliche_kaelteleistung_kw(weather_df, gebaeude)
    summe = jahresenergiemenge_kwh(kaelte)
    assert summe == pytest.approx(float(kaelte.sum()))
