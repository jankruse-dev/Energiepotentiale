"""Definition virtueller Gebäude / Nutzungsrandbedingungen.

Die Randbedingungen (Raum-Solltemperatur, Betriebszeiten,
Außenluftvolumenstrom) orientieren sich an den Nutzungsprofilen für
Nichtwohngebäude (NWG) nach DIN V 18599-10. Für die konkrete Hausarbeit
sind die hier hinterlegten Zahlenwerte projektspezifisch anzupassen bzw.
den Tabellen der DIN V 18599-10 zu entnehmen; sie werden hier als
konfigurierbare Parameter (nicht als Normwerte) behandelt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Betriebszeit:
    """Tägliche Betriebszeit eines Gebäudes/einer Zone.

    ``start_stunde`` und ``end_stunde`` als Stunde des Tages (0..24),
    ``wochentage`` als Menge von Wochentagen (0 = Montag .. 6 = Sonntag).
    """
    start_stunde: int
    end_stunde: int
    wochentage: tuple[int, ...] = (0, 1, 2, 3, 4)  # Mo-Fr

    def ist_betrieb(self, wochentag: int, stunde_im_tag: int) -> bool:
        if wochentag not in self.wochentage:
            return False
        return self.start_stunde <= stunde_im_tag < self.end_stunde


@dataclass
class VirtuellesGebaeude:
    """Virtuelles Nichtwohngebäude für die Lüftungsberechnung.

    ``solltemperatur_kuehlung_c`` und ``feuchte_soll_gpkg`` sind optional
    (``None`` = kein Kühl- bzw. Befeuchtungsfall wird berechnet), da nicht
    jedes Gebäude über eine RLT-Kühlung oder eine Luftbefeuchtung verfügt.
    Analog sind ``druckerhoehung_zuluft_pa``, ``druckerhoehung_abluft_pa``
    und ``wirkungsgrad_ventilator`` optional (``None`` = keine
    Ventilator-Jahresenergiemenge wird berechnet).
    """

    name: str
    nutzungsprofil: str  # z. B. "Einzelbüro", "Lagerhalle" (DIN V 18599-10)
    aussenluftvolumenstrom_m3h: float
    solltemperatur_innen_c: float
    betriebszeit: Betriebszeit
    waermerueckgewinnungsgrad: float = 0.0  # 0 = keine WRG
    solltemperatur_kuehlung_c: float | None = None  # theta_i,c ; None = keine Kühlung
    feuchte_soll_gpkg: float | None = None  # Mindest-Wasserdampfgehalt Zuluft (g/kg); None = keine Befeuchtung
    druckerhoehung_zuluft_pa: float | None = None  # Delta p_ZUL (Pa); None = keine Ventilatorberechnung
    druckerhoehung_abluft_pa: float | None = None  # Delta p_ABL (Pa); None = keine Ventilatorberechnung
    wirkungsgrad_ventilator: float | None = None  # eta_V, Gesamtwirkungsgrad Ventilator/Motor/Antrieb

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "nutzungsprofil": self.nutzungsprofil,
            "aussenluftvolumenstrom_m3h": self.aussenluftvolumenstrom_m3h,
            "solltemperatur_innen_c": self.solltemperatur_innen_c,
            "betriebszeit": {
                "start_stunde": self.betriebszeit.start_stunde,
                "end_stunde": self.betriebszeit.end_stunde,
                "wochentage": list(self.betriebszeit.wochentage),
            },
            "waermerueckgewinnungsgrad": self.waermerueckgewinnungsgrad,
            "solltemperatur_kuehlung_c": self.solltemperatur_kuehlung_c,
            "feuchte_soll_gpkg": self.feuchte_soll_gpkg,
            "druckerhoehung_zuluft_pa": self.druckerhoehung_zuluft_pa,
            "druckerhoehung_abluft_pa": self.druckerhoehung_abluft_pa,
            "wirkungsgrad_ventilator": self.wirkungsgrad_ventilator,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VirtuellesGebaeude":
        bz = data["betriebszeit"]
        return cls(
            name=data["name"],
            nutzungsprofil=data["nutzungsprofil"],
            aussenluftvolumenstrom_m3h=data["aussenluftvolumenstrom_m3h"],
            solltemperatur_innen_c=data["solltemperatur_innen_c"],
            betriebszeit=Betriebszeit(
                start_stunde=bz["start_stunde"],
                end_stunde=bz["end_stunde"],
                wochentage=tuple(bz["wochentage"]),
            ),
            waermerueckgewinnungsgrad=data.get("waermerueckgewinnungsgrad", 0.0),
            solltemperatur_kuehlung_c=data.get("solltemperatur_kuehlung_c"),
            feuchte_soll_gpkg=data.get("feuchte_soll_gpkg"),
            druckerhoehung_zuluft_pa=data.get("druckerhoehung_zuluft_pa"),
            druckerhoehung_abluft_pa=data.get("druckerhoehung_abluft_pa"),
            wirkungsgrad_ventilator=data.get("wirkungsgrad_ventilator"),
        )

    @classmethod
    def from_json(cls, path: str | Path) -> "VirtuellesGebaeude":
        with Path(path).open("r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def to_json(self, path: str | Path) -> None:
        with Path(path).open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
