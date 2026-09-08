"""Definition eines virtuellen Gebaeudes fuer die Lueftungsberechnung.

Die Randbedingungen orientieren sich an den Nutzungsprofilen fuer
Nichtwohngebaeude (NWG) nach DIN V 18599-10. Die hier verwendeten
Zahlenwerte sind fuer die Hausarbeit projektspezifisch gewaehlt bzw. den
Tabellen der DIN V 18599-10 entnommen und keine allgemeinen Normwerte.
"""

import json


class Betriebszeit:
    """Taegliche Betriebszeit eines Gebaeudes.

    start_stunde/end_stunde: Stunde des Tages (0..24)
    wochentage: Liste von Wochentagen (0 = Montag .. 6 = Sonntag)
    """

    def __init__(self, start_stunde, end_stunde, wochentage=(0, 1, 2, 3, 4)):
        self.start_stunde = start_stunde
        self.end_stunde = end_stunde
        self.wochentage = tuple(wochentage)

    def ist_betrieb(self, wochentag, stunde_im_tag):
        if wochentag not in self.wochentage:
            return False
        return self.start_stunde <= stunde_im_tag < self.end_stunde


class Gebaeude:
    """Virtuelles Nichtwohngebaeude fuer die Lueftungsberechnung.

    solltemperatur_kuehlung_c, feuchte_soll_gpkg sowie die Ventilator-
    Parameter sind optional (None = wird nicht berechnet).
    """

    def __init__(
        self,
        name,
        nutzungsprofil,
        aussenluftvolumenstrom_m3h,
        solltemperatur_innen_c,
        betriebszeit,
        waermerueckgewinnungsgrad=0.0,
        solltemperatur_kuehlung_c=None,
        feuchte_soll_gpkg=None,
        druckerhoehung_zuluft_pa=None,
        druckerhoehung_abluft_pa=None,
        wirkungsgrad_ventilator=None,
    ):
        self.name = name
        self.nutzungsprofil = nutzungsprofil
        self.aussenluftvolumenstrom_m3h = aussenluftvolumenstrom_m3h
        self.solltemperatur_innen_c = solltemperatur_innen_c
        self.betriebszeit = betriebszeit
        self.waermerueckgewinnungsgrad = waermerueckgewinnungsgrad
        self.solltemperatur_kuehlung_c = solltemperatur_kuehlung_c
        self.feuchte_soll_gpkg = feuchte_soll_gpkg
        self.druckerhoehung_zuluft_pa = druckerhoehung_zuluft_pa
        self.druckerhoehung_abluft_pa = druckerhoehung_abluft_pa
        self.wirkungsgrad_ventilator = wirkungsgrad_ventilator

    @classmethod
    def aus_json(cls, pfad):
        with open(pfad, "r", encoding="utf-8") as f:
            daten = json.load(f)

        bz = daten["betriebszeit"]
        betriebszeit = Betriebszeit(
            start_stunde=bz["start_stunde"],
            end_stunde=bz["end_stunde"],
            wochentage=bz["wochentage"],
        )

        return cls(
            name=daten["name"],
            nutzungsprofil=daten["nutzungsprofil"],
            aussenluftvolumenstrom_m3h=daten["aussenluftvolumenstrom_m3h"],
            solltemperatur_innen_c=daten["solltemperatur_innen_c"],
            betriebszeit=betriebszeit,
            waermerueckgewinnungsgrad=daten.get("waermerueckgewinnungsgrad", 0.0),
            solltemperatur_kuehlung_c=daten.get("solltemperatur_kuehlung_c"),
            feuchte_soll_gpkg=daten.get("feuchte_soll_gpkg"),
            druckerhoehung_zuluft_pa=daten.get("druckerhoehung_zuluft_pa"),
            druckerhoehung_abluft_pa=daten.get("druckerhoehung_abluft_pa"),
            wirkungsgrad_ventilator=daten.get("wirkungsgrad_ventilator"),
        )
