"""Erstellung der Jahresdauerlinie (JDL) der Lueftungsenergiemengen.

Die JDL entsteht durch absteigendes Sortieren der 8760 Stundenwerte einer
Leistungsgroesse; die Abszisse gibt die Anzahl der Jahresstunden an, in
denen der jeweilige Leistungswert erreicht oder ueberschritten wird.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def jahresdauerlinie(stuendliche_werte):
    """Sortiert die Stundenwerte absteigend, Index = Jahresstunden 1..8760."""
    sortiert = np.sort(stuendliche_werte.to_numpy())[::-1]
    return pd.Series(sortiert, index=pd.RangeIndex(1, len(sortiert) + 1, name="jahresstunden"))


def volllaststunden(stuendliche_werte):
    """Rechnerische Volllaststunden = Jahresenergiemenge / Spitzenleistung."""
    spitze = stuendliche_werte.max()
    if spitze <= 0:
        return 0.0
    return float(stuendliche_werte.sum() / spitze)


def jdl_plotten(jdl, titel, ausgabe_pfad, einheit="kW"):
    """Erstellt und speichert ein Diagramm der Jahresdauerlinie."""
    ausgabe_pfad = Path(ausgabe_pfad)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(jdl.index, jdl.values, linewidth=1.2)
    ax.set_xlabel("Jahresstunden [h]")
    ax.set_ylabel(f"Leistung [{einheit}]")
    ax.set_title(titel)
    ax.set_xlim(0, 8760)
    ax.set_ylim(bottom=0)
    ax.grid(True, linewidth=0.4, alpha=0.6)
    fig.tight_layout()
    fig.savefig(ausgabe_pfad, dpi=200)
    plt.close(fig)
    return ausgabe_pfad
