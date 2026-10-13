"""Les 30 variantes du rejeu VAL (5 stratégies x 3 modèles de fill x 2 conventions bid ET ask), jour par jour.

Une « variante » est une combinaison (stratégie, modèle de fill, convention) : rien n'est choisi sur son résultat,
elles sont toutes publiées. Ce module calcule, pour chacune, le PnL quotidien NET de frais (frais d'exécution et coût de
liquidation déjà déduits dans `O_PNL`) et le nombre d'exécutions quotidiennes ; il en tire les statistiques du README et
du tableau de bord. Seules les années VAL 2019-2022 sont lues (`donnees.py` interdit le TEST).

Unités : pips x lot (1 lot = 1 M EUR, donc 1 pip x 1 lot = 100 USD). Pour le tableau de bord, le rendement quotidien est
rapporté à un capital de référence (CAPITAL_REF_USD) : choix arbitraire qui change l'échelle des courbes et du drawdown en %,
jamais le Sharpe.
"""
import numpy as np
import pandas as pd

from .monte_carlo import JOURS_PAR_AN, ic_bootstrap_blocs, sharpe_annualise
from .rejeu_reel import HORIZONS_MARKOUT, MODELE_BASE, MODELES_FILL, rejouer, resume_markout
from .significativite import dsr, psr, sharpe_quotidien
from .simulateur import O_FRAIS, O_LIQUIDATION, O_NEXEC, O_PNL

GRAINE_REJEU = 20260714
FIN_DE_LIGNE = chr(10)  # fichiers de résultats toujours en LF, même sous Windows
BLOC_JOURS = 10
USD_PAR_PIP_LOT = 100.0
CAPITAL_REF_USD = 100e6         # arbitraire : 5 fois le notionnel de la limite d'inventaire (20 lots x 1 M) ; sans effet sur le Sharpe
FIN_SELECTION = "2020-12-31"    # tableau de bord : sélection 2019-2020, évaluation 2021-2022 (deux moitiés de VAL)
CONVENTIONS = {"adverse": False, "deux_cotes": True}
LIBELLE_CONVENTION = {"adverse": "côté perdant seul", "deux_cotes": "les deux côtés"}
CODE_CONVENTION = {"adverse": "perd", "deux_cotes": "deux"}
CODE_FILL = {"touche": "T", "traversee": "X", "probabiliste": "P"}
CODE_STRATEGIE = {"naif": "NAI", "as": "AS", "as_plafonne": "ASP", "glft": "GLFT", "placebo": "PLA"}
NOM_COURT = {"naif": "Naïve", "as": "Avellaneda-Stoikov", "as_plafonne": "AS skew plafonné", "glft": "GLFT", "placebo": "Placebo"}


def libelle_fill(modele):
    seuil, f = MODELES_FILL[modele]
    return f"{modele} (traversée ≥ {seuil:g} pip, f = {f:g})".replace(".", ",")


def calculer_rejeu(jours, strategies, marche, graine=GRAINE_REJEU):
    """{(modèle de fill, convention): [(sortie, markout, cote_bid, cote_ask) par stratégie]} : les 6 x 5 = 30 rejeux."""
    return {(m, c): [rejouer(jours, s, marche, seuil, f, graine, deux, detail=True) for s in strategies]
            for m, (seuil, f) in MODELES_FILL.items() for c, deux in CONVENTIONS.items()}


def drawdown_max(pnl):
    """Pire baisse du PnL cumulé depuis son sommet (pips x lot, valeur négative ; le sommet initial est 0)."""
    cumul = np.concatenate([[0.0], np.cumsum(pnl)])
    return float((cumul - np.maximum.accumulate(cumul)).min())


def assembler(rejeu, strategies, dates):
    """(DataFrame des PnL quotidiens, DataFrame des exécutions quotidiennes, liste de dicts de statistiques), 30 variantes."""
    index = pd.DatetimeIndex(dates)
    pnl, execs, stats = {}, {}, []
    for (m, c), resultats in rejeu.items():
        for s, (sortie, markout, _, _) in zip(strategies, resultats):
            vid = f"{CODE_STRATEGIE[s.modele]}-{CODE_FILL[m]}-{CODE_CONVENTION[c]}"
            p = sortie[:, O_PNL]
            pnl[vid], execs[vid] = p, sortie[:, O_NEXEC]
            seuil, f = MODELES_FILL[m]
            stats.append({
                "id": vid, "strategie": NOM_COURT[s.modele], "nom_strategie": s.nom, "modele_fill": m, "convention": c,
                "libelle": f"{NOM_COURT[s.modele]}, {libelle_fill(m)}, {LIBELLE_CONVENTION[c]}",
                "seuil_pips": seuil, "f": f, "base": bool(m == MODELE_BASE and c == "adverse"),
                "sharpe": sharpe_annualise(p), "sharpe_ic95_blocs": list(ic_bootstrap_blocs(p, BLOC_JOURS)),
                "pnl_moyen_jour": float(p.mean()), "pnl_ecart_type": float(p.std(ddof=1)), "pnl_cumule": float(p.sum()),
                "drawdown_max": drawdown_max(p), "jours_gagnants": float((p > 0).mean()),
                "executions_par_jour": float(sortie[:, O_NEXEC].mean()),
                "frais_par_jour": float(sortie[:, O_FRAIS].mean()), "liquidation_par_jour": float(sortie[:, O_LIQUIDATION].mean()),
                "markout_pips": {k: v["moyenne_pips"] for k, v in resume_markout(markout).items()},
                "psr0": psr(p, 0.0),
            })
    # DSR : le nombre d'essais est le nombre de variantes publiées ; la variance des Sharpe quotidiens des essais fixe SR0
    essais = np.array([sharpe_quotidien(pnl[d["id"]]) for d in stats])
    for d in stats:
        d["dsr"] = dsr(pnl[d["id"]], essais)
        d["n_essais_dsr"] = len(stats)
    return pd.DataFrame(pnl, index=index), pd.DataFrame(execs, index=index), stats


def ecrire(dossier, pnl, execs, stats, marche):
    """Écrit results/rejeu_pnl_quotidien.csv, rejeu_executions_quotidiennes.csv et rejeu_variantes.json."""
    import json
    pnl.to_csv(dossier / "rejeu_pnl_quotidien.csv", index_label="date", float_format="%.10g", date_format="%Y-%m-%d",
               lineterminator=FIN_DE_LIGNE)
    execs.astype(int).to_csv(dossier / "rejeu_executions_quotidiennes.csv", index_label="date", date_format="%Y-%m-%d",
                             lineterminator=FIN_DE_LIGNE)
    meta = {
        "description": "Les 30 variantes du rejeu VAL 2019-2022 : 5 stratégies x 3 modèles de fill x 2 conventions bid ET ask touchés",
        "unites": "PnL en pips x lot, NET de frais d'exécution et de liquidation ; 1 pip x 1 lot = 100 USD",
        "n_jours": int(len(pnl)), "premier_jour": str(pnl.index[0].date()), "dernier_jour": str(pnl.index[-1].date()),
        "graine_rejeu": GRAINE_REJEU, "bloc_bootstrap_jours": BLOC_JOURS, "annualisation": f"racine de {JOURS_PAR_AN}",
        "frais_pip_par_execution": marche.frais, "demi_spread_liquidation_pips": marche.demi_spread_liq,
        "horizons_markout_min": list(HORIZONS_MARKOUT), "modele_de_base": f"{MODELE_BASE} + adverse",
        "capital_reference_usd": CAPITAL_REF_USD, "usd_par_pip_lot": USD_PAR_PIP_LOT,
        "tableau_de_bord": {"selection": f"{pnl.index[0].date()} -> {FIN_SELECTION}", "evaluation": f"{FIN_SELECTION} -> {pnl.index[-1].date()}"},
        "n_essais_dsr": len(stats),
    }
    texte = json.dumps({"meta": meta, "variantes": stats}, indent=2, ensure_ascii=False) + FIN_DE_LIGNE
    (dossier / "rejeu_variantes.json").write_bytes(texte.encode("utf-8"))  # octets : fins de ligne LF sous Windows aussi
