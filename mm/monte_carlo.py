"""Monte Carlo : même jeu de sessions simulées pour toutes les stratégies (nombres aléatoires communs).

Une session = une journée de PnL ; le Sharpe est donc journalier, annualisé par sqrt(252).
"""
from dataclasses import replace

import numpy as np

from .simulateur import (O_CAPTURE, O_FRAIS, O_INVENTAIRE, O_LIQUIDATION, O_NEXEC,
                         O_PNL, O_QMAX, O_SEL_ADV, construire_params, simuler_matrice)

JOURS_PAR_AN = 252


def sharpe_annualise(pnl):
    pnl = np.asarray(pnl)
    ecart = pnl.std(ddof=1)
    return float(pnl.mean() / ecart * np.sqrt(JOURS_PAR_AN)) if ecart > 0 else float("nan")


def ic_bootstrap_sharpe(pnl, n_boot=2000, graine=0, niveau=0.95):
    """IC percentile du Sharpe par rééchantillonnage des journées (indépendantes en simulation ; approximation sur données réelles)."""
    pnl = np.asarray(pnl)
    idx = np.random.default_rng(graine).integers(0, pnl.size, (n_boot, pnl.size))
    x = pnl[idx]
    sharpes = x.mean(axis=1) / x.std(axis=1, ddof=1) * np.sqrt(JOURS_PAR_AN)
    bas, haut = np.percentile(sharpes, [50 * (1 - niveau), 100 - 50 * (1 - niveau)])
    return float(bas), float(haut)


def ic_bootstrap_blocs(pnl, bloc=10, n_boot=2000, graine=0, niveau=0.95):
    """IC du Sharpe par bootstrap circulaire PAR BLOCS de `bloc` jours consécutifs.

    Les PnL journaliers réels sont autocorrélés (régimes de volatilité) : rééchantillonner les
    jours un par un sous-estime l'incertitude. Longueur de bloc fixée a priori (2 semaines de bourse), pas optimisée.
    """
    pnl = np.asarray(pnl)
    n = pnl.size
    n_blocs = int(np.ceil(n / bloc))
    debuts = np.random.default_rng(graine).integers(0, n, (n_boot, n_blocs, 1))
    idx = ((debuts + np.arange(bloc)) % n).reshape(n_boot, -1)[:, :n]
    x = pnl[idx]
    sharpes = x.mean(axis=1) / x.std(axis=1, ddof=1) * np.sqrt(JOURS_PAR_AN)
    bas, haut = np.percentile(sharpes, [50 * (1 - niveau), 100 - 50 * (1 - niveau)])
    return float(bas), float(haut)


def cvar(pnl, niveau=0.05):
    """Moyenne des pires `niveau` des journées (négatif = perte)."""
    pire = np.sort(np.asarray(pnl))[: max(1, int(np.ceil(niveau * len(pnl))))]
    return float(pire.mean())


def resumer(res, bloc=None):
    """Statistiques d'une stratégie à partir de son tableau (n_sessions, N_OUT).

    bloc=None : sessions simulées indépendantes -> bootstrap simple. bloc=10 : jours réels -> bootstrap par blocs
    (l'IC « iid » est alors donné en plus, pour voir ce que l'autocorrélation change).
    """
    pnl = res[:, O_PNL]
    iid = ic_bootstrap_sharpe(pnl)
    bas, haut = iid if bloc is None else ic_bootstrap_blocs(pnl, bloc)
    return {
        "sharpe_annualise": sharpe_annualise(pnl),
        "sharpe_ic95": [bas, haut],
        **({} if bloc is None else {"sharpe_ic95_iid": list(iid), "bloc_jours": bloc}),
        "pnl_moyen_pips_lot": float(pnl.mean()),
        "pnl_ecart_type": float(pnl.std(ddof=1)),
        "proba_perte": float((pnl < 0).mean()),
        "cvar_5pct": cvar(pnl),
        "inventaire_max_moyen": float(res[:, O_QMAX].mean()),
        "inventaire_max_p95": float(np.percentile(res[:, O_QMAX], 95)),
        "executions_moyennes": float(res[:, O_NEXEC].mean()),
        "decomposition_moyenne": {
            "capture_spread": float(res[:, O_CAPTURE].mean()),
            "inventaire_total": float(res[:, O_INVENTAIRE].mean()),
            "dont_selection_adverse": float(res[:, O_SEL_ADV].mean()),
            "cout_liquidation": float(-res[:, O_LIQUIDATION].mean()),
            "frais": float(-res[:, O_FRAIS].mean()),
        },
    }


def monte_carlo(strategies, marche, n_sessions=2000, graine=20260713):
    """(n_strategies, n_sessions, N_OUT) : toutes les stratégies voient les mêmes sessions."""
    params = np.array([construire_params(s, marche) for s in strategies])
    return simuler_matrice(params, n_sessions, graine, marche.n_pas)


def _sharpes_et_pnl(lignes_params, n_sessions, graine, n_pas):
    res = simuler_matrice(np.array(lignes_params), n_sessions, graine, n_pas)
    pnl = res[:, :, O_PNL]
    return np.array([sharpe_annualise(x) for x in pnl]), pnl.mean(axis=1)


def balayage_1d(strategies, marche, champ, valeurs, n_sessions=500, graine=777, cote="marche"):
    """Sharpe de chaque stratégie quand `champ` (du marché ou de la stratégie) prend successivement `valeurs`."""
    lignes = []
    for v in valeurs:
        for s in strategies:
            m2, s2 = (replace(marche, **{champ: v}), s) if cote == "marche" else (marche, replace(s, **{champ: v}))
            lignes.append(construire_params(s2, m2))
    sharpe, pnl = _sharpes_et_pnl(lignes, n_sessions, graine, marche.n_pas)
    forme = (len(valeurs), len(strategies))
    return sharpe.reshape(forme), pnl.reshape(forme)


def grille_2d(strategie, marche, axe_lignes, axe_colonnes, n_sessions=500, graine=777):
    """Sharpe (et PnL moyen) d'une stratégie sur une grille 2D.

    Un axe = (cote, champ, valeurs) avec cote "marche" ou "strategie" ; les nombres aléatoires
    sont communs à toutes les cellules, donc les écarts entre cellules ne sont pas du bruit d'échantillonnage.
    """
    def appliquer(m, s, axe, v):
        cote, champ, _ = axe
        return (replace(m, **{champ: v}), s) if cote == "marche" else (m, replace(s, **{champ: v}))

    lignes = []
    for vl in axe_lignes[2]:
        for vc in axe_colonnes[2]:
            m, s = appliquer(marche, strategie, axe_lignes, vl)
            m, s = appliquer(m, s, axe_colonnes, vc)
            lignes.append(construire_params(s, m))
    sharpe, pnl = _sharpes_et_pnl(lignes, n_sessions, graine, marche.n_pas)
    forme = (len(axe_lignes[2]), len(axe_colonnes[2]))
    return sharpe.reshape(forme), pnl.reshape(forme)


def grille_A_k(strategies, marche, valeurs_A, valeurs_k, n_sessions=500, graine=777):
    """Sensibilité 3x3 aux VRAIS A et k du marché (la stratégie garde ses croyances) : (len(A), len(k), n_strat)."""
    lignes = [construire_params(s, replace(marche, A=a, k=k)) for a in valeurs_A for k in valeurs_k for s in strategies]
    sharpe, _ = _sharpes_et_pnl(lignes, n_sessions, graine, marche.n_pas)
    return sharpe.reshape(len(valeurs_A), len(valeurs_k), len(strategies))
