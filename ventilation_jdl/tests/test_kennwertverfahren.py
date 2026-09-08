import pytest

from ventilation_jdl.kennwertverfahren import (
    KennwertRandbedingungen,
    VARIANTE_21_JAHR,
    jahres_heizenergiebedarf_kwh,
    jahres_kaelteenergiebedarf_kwh,
    jahres_dampfbefeuchtungsenergiebedarf_kwh,
)


def test_jahres_heizenergiebedarf_buerogebaeude_variante3():
    """Vergleichsrechnung für das Einzelbüro-Profil (V=500 m3/h,
    theta_hc=20°C, 7-18 Uhr Mo-Fr => 11 h/Tag, 260 Betriebstage/Jahr)
    gegen den von Hand nachgerechneten Wert aus DIN V 18599-3,
    Tabelle A.1, Variante 3 (~880 kWh/a)."""
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=500.0,
        zulufttemperatur_soll_c=20.0,
        taegliche_betriebsstunden=11.0,
        jaehrliche_betriebstage=260.0,
    )
    ergebnis = jahres_heizenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(880.0, rel=0.02)


def test_qh_bei_theta_18_liefert_basiskennwert():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1.0,
        zulufttemperatur_soll_c=18.0,
        taegliche_betriebsstunden=12.0,
        jaehrliche_betriebstage=365.0,
    )
    ergebnis = jahres_heizenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(1.148, rel=1e-6)


def test_zulufttemperatur_ausserhalb_gueltigkeitsbereich_wirft_fehler():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=500.0,
        zulufttemperatur_soll_c=25.0,
        taegliche_betriebsstunden=11.0,
        jaehrliche_betriebstage=260.0,
    )
    with pytest.raises(ValueError):
        jahres_heizenergiebedarf_kwh(randbedingungen)


def test_jahres_kaelteenergiebedarf_am_gueltigkeitsrand_22c():
    """Vergleichsrechnung Kühlfall am oberen Rand des Gültigkeitsbereichs
    der Umrechnungsgleichungen (22 °C statt der realen, außerhalb des
    Gültigkeitsbereichs liegenden Raum-Kühlsolltemperatur 24 °C nach
    DIN V 18599-10)."""
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=500.0,
        zulufttemperatur_soll_c=22.0,
        taegliche_betriebsstunden=11.0,
        jaehrliche_betriebstage=260.0,
    )
    ergebnis = jahres_kaelteenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(249.5, rel=0.01)


def test_kaelteenergiebedarf_ausserhalb_gueltigkeitsbereich_wirft_fehler():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=500.0,
        zulufttemperatur_soll_c=24.0,
        taegliche_betriebsstunden=11.0,
        jaehrliche_betriebstage=260.0,
    )
    with pytest.raises(ValueError):
        jahres_kaelteenergiebedarf_kwh(randbedingungen)


def test_betriebsstunden_ausserhalb_gueltigkeitsbereich_wirft_fehler():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=500.0,
        zulufttemperatur_soll_c=20.0,
        taegliche_betriebsstunden=2.0,
        jaehrliche_betriebstage=260.0,
    )
    with pytest.raises(ValueError):
        jahres_heizenergiebedarf_kwh(randbedingungen)


def test_jahres_heizenergiebedarf_serverraum_variante3_korrigiert():
    """Serverraum-Profil (V=1500 m3/h, theta_hc=21°C, 24 h/Tag,
    365 Betriebstage/Jahr) nach DIN V 18599-10, Tabelle A.21
    (Feuchteanforderung "keine") gegen Variante 3 (keine
    Feuchteanforderung) der DIN V 18599-3, Tabelle A.1."""
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1500.0,
        zulufttemperatur_soll_c=21.0,
        taegliche_betriebsstunden=24.0,
        jaehrliche_betriebstage=365.0,
    )
    ergebnis = jahres_heizenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(11120.5, rel=0.01)


def test_jahres_kaelteenergiebedarf_serverraum_variante3_korrigiert():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1500.0,
        zulufttemperatur_soll_c=22.0,  # gecappt, reale theta_i,c = 24°C
        taegliche_betriebsstunden=24.0,
        jaehrliche_betriebstage=365.0,
    )
    ergebnis = jahres_kaelteenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(1490.9, rel=0.01)


def test_jahres_heizenergiebedarf_grossraumbuero_variante21():
    """Großraumbüro-Profil (V=1200 m3/h, theta_hc=21°C, 13 h/Tag,
    250 Betriebstage/Jahr) nach DIN V 18599-10, Tabelle A.3
    (Feuchteanforderung "mit Toleranz") gegen Variante 21 (mit
    Toleranzbereich, Dampfbefeuchter) der DIN V 18599-3, Tabelle A.1."""
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1200.0,
        zulufttemperatur_soll_c=21.0,
        taegliche_betriebsstunden=13.0,
        jaehrliche_betriebstage=250.0,
    )
    ergebnis = jahres_heizenergiebedarf_kwh(randbedingungen, VARIANTE_21_JAHR)
    assert ergebnis == pytest.approx(3290.5, rel=0.01)


def test_jahres_kaelteenergiebedarf_grossraumbuero_variante21():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1200.0,
        zulufttemperatur_soll_c=22.0,  # gecappt, reale theta_i,c = 24°C
        taegliche_betriebsstunden=13.0,
        jaehrliche_betriebstage=250.0,
    )
    ergebnis = jahres_kaelteenergiebedarf_kwh(randbedingungen, VARIANTE_21_JAHR)
    assert ergebnis == pytest.approx(1277.7, rel=0.01)


def test_jahres_dampfbefeuchtungsenergiebedarf_grossraumbuero_variante21():
    randbedingungen = KennwertRandbedingungen(
        aussenluftvolumenstrom_m3h=1200.0,
        zulufttemperatur_soll_c=21.0,
        taegliche_betriebsstunden=13.0,
        jaehrliche_betriebstage=250.0,
    )
    ergebnis = jahres_dampfbefeuchtungsenergiebedarf_kwh(randbedingungen)
    assert ergebnis == pytest.approx(3554.5, rel=0.01)
