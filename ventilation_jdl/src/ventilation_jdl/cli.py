"""Kommandozeilen-Einstieg für die überschlägige Jahresenergiemenge der
Lüftung und die Jahresdauerlinie.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .building import VirtuellesGebaeude
from .load_duration import jahresdauerlinie, plot_jahresdauerlinie, volllaststunden
from .ventilation import jahresenergiemenge_kwh, stuendlicher_waermeverlust_kw
from .weather import read_try_file


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Überschlägige Berechnung der Jahresenergiemenge der Lüftung "
            "und Erstellung der Jahresdauerlinie."
        )
    )
    parser.add_argument("--try-file", required=True, help="Pfad zur DWD-TRY-Datei")
    parser.add_argument(
        "--profile", required=True, help="Pfad zur Gebäudeprofil-JSON-Datei"
    )
    parser.add_argument(
        "--output", default="results", help="Ausgabeverzeichnis (Standard: results/)"
    )
    return parser.parse_args(argv)


def main(argv=None) -> None:
    args = parse_args(argv)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    weather_df = read_try_file(args.try_file)
    gebaeude = VirtuellesGebaeude.from_json(args.profile)

    stuendlich_kw = stuendlicher_waermeverlust_kw(weather_df, gebaeude)
    q_jahr_kwh = jahresenergiemenge_kwh(stuendlich_kw)
    jdl = jahresdauerlinie(stuendlich_kw)
    vlh = volllaststunden(stuendlich_kw)

    stuendlich_kw.to_csv(output_dir / f"{gebaeude.name}_stundenwerte.csv")
    jdl.to_csv(output_dir / f"{gebaeude.name}_jahresdauerlinie.csv")
    plot_jahresdauerlinie(
        jdl,
        titel=f"Jahresdauerlinie Lüftungswärmeverlust – {gebaeude.name}",
        output_path=output_dir / f"{gebaeude.name}_jahresdauerlinie.png",
    )

    print(f"Gebäude: {gebaeude.name} ({gebaeude.nutzungsprofil})")
    print(f"Jahresenergiemenge Lüftung: {q_jahr_kwh:.0f} kWh")
    print(f"Rechnerische Volllaststunden: {vlh:.0f} h")
    print(f"Ergebnisse gespeichert in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
