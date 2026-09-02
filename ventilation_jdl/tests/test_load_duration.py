import pandas as pd

from ventilation_jdl.load_duration import jahresdauerlinie, volllaststunden


def test_jahresdauerlinie_ist_absteigend_sortiert():
    werte = pd.Series([1.0, 5.0, 3.0, 0.0, 4.0])
    jdl = jahresdauerlinie(werte)
    assert list(jdl.values) == sorted(werte.values, reverse=True)
    assert list(jdl.index) == list(range(1, 6))


def test_volllaststunden_bei_konstanter_last():
    werte = pd.Series([2.0] * 10)
    vlh = volllaststunden(werte)
    assert vlh == 10.0


def test_volllaststunden_bei_nulllast():
    werte = pd.Series([0.0, 0.0, 0.0])
    assert volllaststunden(werte) == 0.0
