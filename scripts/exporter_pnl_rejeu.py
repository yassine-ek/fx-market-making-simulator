"""Recalcule les 30 variantes du rejeu VAL et écrit leur PnL quotidien dans results/ (données de marché requises).

Lit les hypothèses (marché simulé, 5 stratégies) dans results/verdict_mm.json, donc pas de recalibration de sigma :
seules les années VAL 2019-2022 sont lues (HISTDATA_DIR). Vérifie que le Sharpe de chaque variante coïncide avec celui de
verdict_mm.json (même graine, mêmes données : égalité à 1e-9) avant d'écrire.
Écrit results/rejeu_pnl_quotidien.csv, results/rejeu_executions_quotidiennes.csv, results/rejeu_variantes.json.
`scripts/run_all.py` fait la même chose en fin de chaîne.

Usage : HISTDATA_DIR=... python scripts/exporter_pnl_rejeu.py
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from mm.donnees import ANNEES_VAL, dossier_donnees  # noqa: E402
from mm.modeles import Strategie  # noqa: E402
from mm.rejeu_reel import construire_jours  # noqa: E402
from mm.simulateur import Marche  # noqa: E402
from mm.variantes_rejeu import assembler, calculer_rejeu, ecrire  # noqa: E402


def verifier_contre_verdict(stats, verdict):
    """Le CSV ne doit jamais dériver de verdict_mm.json : écart de Sharpe > 1e-9 = résultats périmés."""
    par_fill = verdict["rejeu_val"]["par_modele_de_fill"]
    for d in stats:
        attendu = par_fill[d["modele_fill"]][d["convention"]][d["nom_strategie"]]["sharpe_annualise"]
        if abs(d["sharpe"] - attendu) > 1e-9:
            raise SystemExit(f"{d['id']} : Sharpe {d['sharpe']} != {attendu} (verdict_mm.json périmé ? relancer run_all.py)")


def main():
    if not (dossier_donnees() / "EURUSD_2019.zip").exists():
        sys.exit("Données absentes : définir HISTDATA_DIR (racine contenant histdata_raw/EURUSD/EURUSD_<année>.zip).")
    verdict = json.loads((RACINE / "results" / "verdict_mm.json").read_text(encoding="utf-8"))
    hyp = verdict["hypotheses"]
    marche = Marche(**hyp["marche_simule"])
    strategies = [Strategie(**s) for s in hyp["strategies"].values()]
    jours = construire_jours(ANNEES_VAL, hyp["hypotheses_non_mesurees"]["demi_spread_marche"])
    pnl, execs, stats = assembler(calculer_rejeu(jours, strategies, marche), strategies, jours["dates"].astype("datetime64[D]"))
    verifier_contre_verdict(stats, verdict)
    ecrire(RACINE / "results", pnl, execs, stats, marche)
    print(f"results/rejeu_pnl_quotidien.csv, rejeu_executions_quotidiennes.csv, rejeu_variantes.json : "
          f"{len(stats)} variantes, {len(pnl)} jours ({pnl.index[0].date()} -> {pnl.index[-1].date()})")


if __name__ == "__main__":
    main()
