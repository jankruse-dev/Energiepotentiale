"""Erstellung der Jahresdauerlinie (JDL) der Lüftungswärmeverluste.

Die Jahresdauerlinie entsteht durch absteigendes Sortieren der 8760
Stundenwerte einer Leistungsgröße; die Abszisse gibt die Anzahl der
Stunden im Jahr an, in denen der jeweilige Leistungswert erreicht oder
überschritten wird.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def jahresdauerlinie(stuendliche_werte: pd.Series) -> pd.Series:
    """Sortiert die stündlichen Werte absteigend und liefert die JDL.

    Der Index der zurückgegebenen Series entspricht der Anzahl der
    Jahresstunden (1..8760), die Werte der jeweils erreichten/
    überschrittenen Leistung.
    """
    sortiert = np.sort(stuendliche_werte.to_numpy())[::-1]
    return pd.Series(sortiert, index=pd.RangeIndex(1, len(sortiert) + 1, name="jahresstunden"))


def volllaststunden(stuendliche_werte: pd.Series) -> float:
    """Rechnerische Volllaststunden: Jahresenergiemenge / Spitzenleistung."""
    spitze = stuendliche_werte.max()
    if spitze <= 0:
        return 0.0
    return float(stuendliche_werte.sum() / spitze)


def plot_jahresdauerlinie(
    jdl: pd.Series, titel: str, output_path: str | Path, einheit: str = "kW"
) -> Path:
    """Erstellt und speichert eine Abbildung der Jahresdauerlinie."""
    output_path = Path(output_path)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(jdl.index, jdl.values, linewidth=1.2)
    ax.set_xlabel("Jahresstunden [h]")
    ax.set_ylabel(f"Lüftungswärmeverlust [{einheit}]")
    ax.set_title(titel)
    ax.set_xlim(0, 8760)
    ax.set_ylim(bottom=0)
    ax.grid(True, linewidth=0.4, alpha=0.6)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200)
    plt.close(fig)
    return output_path
