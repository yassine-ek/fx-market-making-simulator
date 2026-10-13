"""Exporte le tableau de bord interactif (gabarit commun des tableaux de bord du portfolio, copié dans docs/index.html) dans docs/.

Lit UNIQUEMENT des fichiers de results/ (aucune donnée de marché requise, donc exécutable en CI) :
  - results/rejeu_pnl_quotidien.csv          PnL quotidien NET des 30 variantes du rejeu VAL 2019-2022 (pips x lot)
  - results/rejeu_executions_quotidiennes.csv  nombre d'exécutions par jour et par variante
  - results/rejeu_variantes.json             libellés et statistiques des variantes
  - results/verdict_mm.json                  hypothèses (frais, spread, A, k, p, alpha)
Écrit docs/data.json, docs/data.js (même contenu, pour l'ouverture en file://), docs/index.html (copie du gabarit s'il est
présent à côté du dépôt, sinon on garde celui de docs/) et docs/.nojekyll.

Adaptation du gabarit : le rejeu ne couvre que VAL 2019-2022, il n'existe donc pas de TRAIN rejoué. On coupe VAL en deux :
  première période du gabarit (« train ») = SÉLECTION 2019-2020 (les filtres n'utilisent que cette période),
  seconde période (« val ») = ÉVALUATION 2021-2022 (la courbe y est lue sans avoir servi à la sélection).
Les frontières sont dans data.frontieres (train_fin = 2020-12-31, val_fin = 2022-12-31) et les noms affichés dans
data.libelles (champ du gabarit qui remplace « TRAIN » et « VAL » dans toute la page). Aucune donnée >= 2023.

Usage : python scripts/exporter_dashboard.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from mm.variantes_rejeu import CAPITAL_REF_USD, FIN_SELECTION, LIBELLE_CONVENTION, USD_PAR_PIP_LOT  # noqa: E402

RESULTATS = RACINE / "results"
DOCS = RACINE / "docs"
GABARIT = RACINE.parent / "_outils" / "dashboard" / "index.html"  # présent dans le dépôt du portfolio, absent d'un dépôt isolé
FIN_VAL = "2022-12-31"
FILL_AFFICHE = {"touche": "touche", "traversee": "traversée", "probabiliste": "probabiliste"}


def _chiffre(x: float) -> float:
    return float(f"{x:.8g}")


def _fr(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}".replace(".", ",")


def sharpe(x: np.ndarray) -> float:
    return float(x.mean() / x.std(ddof=1) * np.sqrt(252))


def texte_frais(verdict: dict) -> str:
    h = verdict["hypotheses"]["hypotheses_non_mesurees"]
    return (f"Frais d'exécution {_fr(h['frais'])} pip par exécution et demi-spread de liquidation {_fr(h['demi_spread_marche'], 2)} pip "
            f"(hypothèses, aucune donnée d'ordres), PnL net déjà déduit de ces coûts ; 1 pip × 1 lot (1 M EUR) = 100 USD. "
            f"Rejeu sur barres EURUSD 1 minute HistData (prix BID, heure de New York), demi-spread de marché {_fr(h['demi_spread_marche'], 2)} pip ajouté, "
            f"cote de la minute i calculée sur le close de i-1 (latence implicite de 60 s). « Côté perdant seul » : quand bid et ask sont touchés dans la même barre, "
            f"le côté exécuté est choisi avec le close de la barre, un choix pessimiste fait a posteriori et non un fill réaliste. Hypothèses du simulateur, non utilisées ici : "
            f"A = {_fr(h['A'], 2)} /s, k = {_fr(h['k'], 1)}, p = {_fr(h['p_adverse'], 2)}, α = {_fr(h['alpha'], 2)} pip. "
            f"Rendement quotidien = PnL net en USD / {CAPITAL_REF_USD / 1e6:.0f} M USD (capital de référence arbitraire : il change l'échelle des "
            f"courbes et des drawdowns en %, jamais le Sharpe). TRAIN ≤ 2018 sert uniquement à calibrer σ ; TEST 2023+ scellé, jamais lu.")


def main() -> None:
    verdict = json.loads((RESULTATS / "verdict_mm.json").read_text(encoding="utf-8"))
    meta_var = json.loads((RESULTATS / "rejeu_variantes.json").read_text(encoding="utf-8"))
    pnl = pd.read_csv(RESULTATS / "rejeu_pnl_quotidien.csv", index_col=0, parse_dates=True)
    execs = pd.read_csv(RESULTATS / "rejeu_executions_quotidiennes.csv", index_col=0, parse_dates=True)
    assert pnl.index.max() <= pd.Timestamp(FIN_VAL), "le TEST ne doit jamais apparaître"
    assert list(pnl.columns) == list(execs.columns) == [v["id"] for v in meta_var["variantes"]]
    dates = [d.strftime("%Y-%m-%d") for d in pnl.index]
    selection = pnl.index <= pd.Timestamp(FIN_SELECTION)

    variantes = []
    for v in meta_var["variantes"]:
        p = pnl[v["id"]].to_numpy()
        e = execs[v["id"]].to_numpy()
        stats = {
            "nb_trades_train": int(e[selection].sum()), "nb_trades_val": int(e[~selection].sum()),
            "sharpe_train": round(sharpe(p[selection]), 4), "sharpe_val": round(sharpe(p[~selection]), 4),
            "pnl_jour_train": round(float(p[selection].mean()), 2), "pnl_jour_val": round(float(p[~selection].mean()), 2),
        }
        variantes.append({
            "id": v["id"], "libelle": v["libelle"], "groupe": v["strategie"], "strategie": v["strategie"],
            "modele_fill": FILL_AFFICHE[v["modele_fill"]], "convention": LIBELLE_CONVENTION[v["convention"]],
            "debut": dates[0], "rendements": [_chiffre(x * USD_PAR_PIP_LOT / CAPITAL_REF_USD) for x in p], "stats": stats,
        })

    filtres = [
        {"cle": "nb_trades_train", "libelle": "Nb d'exécutions min (période de sélection 2019-2020)", "type": "min"},
        {"cle": "sharpe_train", "libelle": "Sharpe min (période de sélection 2019-2020)", "type": "min", "pas": 0.5},
        {"cle": "strategie", "libelle": "Stratégie", "type": "choix"},
        {"cle": "modele_fill", "libelle": "Modèle de fill", "type": "choix"},
        {"cle": "convention", "libelle": "Si bid ET ask touchés dans la même barre", "type": "choix"},
    ]
    data = {
        "titre": "FX market making : simulation vs rejeu réel",
        "description": "Simulateur de market making FX (Avellaneda-Stoikov, GLFT) : 30 variantes rejouées sur EURUSD 1 minute réel, comparées à la simulation.",
        "libelles": {"train": "SÉLECTION 2019-2020", "val": "ÉVALUATION 2021-2022"},
        "sous_titre": ("Les deux périodes de la page sont la SÉLECTION 2019-2020 et l'ÉVALUATION 2021-2022 : les deux moitiés de la VAL 2019-2022 du dépôt. "
                       "Le rejeu ne couvre pas TRAIN ≤ 2018 (qui sert seulement à calibrer σ) et le TEST 2023+ est scellé. Filtrer les 30 variantes (5 stratégies × 3 modèles de fill × 2 conventions) sur "
                       "leurs statistiques de 2019-2020, combiner celles qui restent, lire la courbe sur 2021-2022. Les 30 variantes sont fixées a priori ; "
                       "toutes ont un Sharpe négatif : le filtre ne peut pas créer d'edge, il montre seulement ce que coûte la convention de fill."),
        "frais": texte_frais(verdict),
        "frontieres": {"train_fin": FIN_SELECTION, "val_fin": FIN_VAL},
        "dates": dates,
        "variantes": variantes,
        "filtres": filtres,
        "combinaison": "moyenne",
    }
    texte = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data.json").write_bytes(texte.encode("utf-8"))
    (DOCS / "data.js").write_bytes(("window.DATA = " + texte + ";" + chr(10)).encode("utf-8"))
    (DOCS / ".nojekyll").write_bytes(b"")
    if GABARIT.exists():
        shutil.copyfile(GABARIT, DOCS / "index.html")
    assert (DOCS / "index.html").exists(), "docs/index.html manquant (gabarit introuvable)"
    print(f"docs/data.json + data.js : {len(texte) / 1e6:.2f} Mo, {len(dates)} dates ({dates[0]} -> {dates[-1]}), {len(variantes)} variantes")


if __name__ == "__main__":
    main()
