"""Rejeu des stratégies sur les barres 1-minute EURUSD réelles (VAL 2019-2022).

ATTENTION, rejeu APPROXIMATIF : pas de carnet L2, pas de file d'attente réelle, toujours 1 lot, pas
d'impact. Optimiste sur ces points ; pessimiste sur la traversée du MID et le côté unique. Une barre
résume 60 secondes de prix : les règles ci-dessous sont des conventions, pas une reconstitution du marché.

Règles (une session = une journée, 541 barres de 02:59 à 11:59, heure de New York, on cote à partir de 03:00) :
  - référence causale : mid_ref(i) = close(i-1) + demi-spread de marché (HistData = BID -> mid) ;
  - cotes = mid_ref -/+ profondeurs du modèle (il n'utilise que des données <= i-1) ;
  - MODÈLE DE FILL (le résultat central du rejeu est la sensibilité du Sharpe à ce choix) :
      "touche"       : le bid est exécuté si le plus bas de la barre i atteint la cote (traversée >= 0), f = 1 ;
      "traversee"    : il faut la dépasser d'au moins 0,1 pip (toucher ne suffit pas), f = 1 ;
      "probabiliste" : traversée >= 0,1 pip ET exécution seulement avec probabilité f = 0,5 (file d'attente) ;
  - si bid ET ask sont atteints dans la même barre, l'ordre intra-barre est inconnu : on suppose l'ordre
    DÉFAVORABLE, le côté qui perd (celui dont le close s'éloigne) passe en premier. Deux lectures, présentées
    toutes les deux car elles encadrent la vérité :
      "adverse"    : seul ce côté perdant est exécuté (borne pessimiste ; c'est le cas de base) ;
      "deux_cotes" : le côté perdant d'abord, puis l'autre aussi (borne optimiste : aller-retour à chaque barre).
    Le close de la barre i sert à décider du fill, jamais à coter ;
  - inventaire valorisé au close de chaque barre ; liquidation finale à mid -/+ demi-spread ;
  - MARKOUT : chaque exécution est revalorisée au mid h minutes plus tard (h = 1, 5, 15).
"""
import numpy as np
import pandas as pd
from numba import njit, prange

from .donnees import charger_annee
from .modeles import profondeurs_strategie
from .simulateur import (I_A_MOD, I_CAP, I_CODE, I_DEMI_NAIF, I_FRAIS, I_GAMMA, I_HLIQ, I_K_MOD, I_Q,
                         I_SIG_MOD, N_OUT, O_CAPTURE, O_FRAIS, O_INVENTAIRE, O_LIQUIDATION, O_NEXEC, O_PNL,
                         O_PNL_CASH, O_QFINAL, O_QMAX, construire_params)

MIN_DEBUT, MIN_FIN = 179, 719  # 02:59 et 11:59 (heure de New York), en minutes depuis minuit
N_BARRES = MIN_FIN - MIN_DEBUT + 1  # 541 : la barre 0 ne sert que de référence
HORIZONS_MARKOUT = (1, 5, 15)  # minutes
MODELES_FILL = {"touche": (0.0, 1.0), "traversee": (0.1, 1.0), "probabiliste": (0.1, 0.5)}  # (seuil en pips, f)
MODELE_BASE = "probabiliste"


def construire_jours(annees, demi_spread_marche, min_barres=450):
    """Tableaux (n_jours, 541) open/high/low/close en MID (pips) + masque des barres réelles + dates."""
    blocs = []
    for annee in annees:
        b = charger_annee(annee)
        minute = (b.index.hour * 60 + b.index.minute).to_numpy()
        garde = (minute >= MIN_DEBUT) & (minute <= MIN_FIN)
        b, pos = b[garde], minute[garde] - MIN_DEBUT
        jours, inv = np.unique(b.index.normalize().to_numpy(), return_inverse=True)
        tab = np.full((len(jours), 4, N_BARRES), np.nan)
        tab[inv, :, pos] = b[["open", "high", "low", "close"]].to_numpy()
        blocs.append((jours, tab))
    dates = np.concatenate([j for j, _ in blocs])
    tab = np.concatenate([t for _, t in blocs])
    valide = ~np.isnan(tab[:, 3, :])
    ok = valide.sum(axis=1) >= min_barres  # écarte jours fériés et sessions tronquées
    dates, tab, valide = dates[ok], tab[ok], valide[ok]
    # barre manquante = barre plate au dernier close connu (jamais d'exécution dessus, grâce au masque)
    close = pd.DataFrame(tab[:, 3, :]).ffill(axis=1).bfill(axis=1).to_numpy()
    tab[:, 3, :] = close
    for c in range(3):
        tab[:, c, :] = np.where(np.isnan(tab[:, c, :]), close, tab[:, c, :])
    tab += demi_spread_marche
    return {"dates": dates, "O": tab[:, 0], "H": tab[:, 1], "L": tab[:, 2], "C": tab[:, 3], "valide": valide}


def jours_marche_aleatoire(n_jours, sigma_minute, graine=0, pas_s=1, base=1e4):
    """CONTRÔLE : journées de barres 1 min tirées d'une marche aléatoire SANS dérive (pas de `pas_s` s dans la barre).

    Même format que `construire_jours`. Sert à vérifier ce que le rejeu mesure sur un marché qui n'a, par
    construction, aucune sélection adverse : si le markout y est déjà négatif, il vient de la convention de fill.
    """
    n_sub = int(round(60 / pas_s))
    z = np.random.default_rng(graine).standard_normal((n_jours, N_BARRES * n_sub))
    chemin = np.cumsum(z * sigma_minute * np.sqrt(pas_s / 60.0), axis=1).reshape(n_jours, N_BARRES, n_sub)
    c = chemin[:, :, -1]
    o = np.concatenate([np.zeros((n_jours, 1)), c[:, :-1]], axis=1)  # open = close précédent
    return {"dates": np.arange(n_jours), "O": o + base, "H": np.maximum(chemin.max(axis=2), o) + base,
            "L": np.minimum(chemin.min(axis=2), o) + base, "C": c + base, "valide": np.ones((n_jours, N_BARRES), bool)}


@njit(parallel=True, cache=True)
def _rejouer(H, L, C, valide, ub, ua, wb, wa, p, f, seuil, deux_cotes, horizons, sortie, markout, cote_bid, cote_ask):
    n_jours, n_barres = C.shape
    borne = p[I_Q]
    for d in prange(n_jours):
        q = cash = capture = inv = frais_tot = q_max = 0.0
        n_exec = 0
        for i in range(1, n_barres):
            ref = C[d, i - 1]  # close de la minute précédente : seule information utilisée pour coter
            tau = (n_barres - i) * 60.0
            db, da = profondeurs_strategie(int(p[I_CODE]), q, tau, p[I_GAMMA], p[I_SIG_MOD], p[I_K_MOD],
                                           p[I_A_MOD], p[I_DEMI_NAIF], p[I_CAP], wb[d, i], wa[d, i])
            bid, ask = ref - max(db, 0.0), ref + max(da, 0.0)
            cote_bid[d, i], cote_ask[d, i] = bid, ask
            peut_bid = q < borne and valide[d, i] and L[d, i] <= bid - seuil
            peut_ask = q > -borne and valide[d, i] and H[d, i] >= ask + seuil
            cote1 = cote2 = 0
            if peut_bid and peut_ask:  # ordre intra-barre inconnu : on suppose le pire (côté qui perd d'abord)
                cote1 = 1 if C[d, i] - bid <= ask - C[d, i] else -1
                cote2 = -cote1 if deux_cotes else 0
            elif peut_bid:
                cote1 = 1
            elif peut_ask:
                cote1 = -1
            for etape in range(2):
                cote = cote1 if etape == 0 else cote2
                if cote == 0 or (ub[d, i] if cote == 1 else ua[d, i]) >= f:
                    continue
                prix = bid if cote == 1 else ask
                q += cote
                cash -= cote * prix + p[I_FRAIS]
                capture += cote * (ref - prix)
                frais_tot += p[I_FRAIS]
                n_exec += 1
                for j in range(horizons.shape[0]):  # markout : évaluation seulement, rien n'en dépend
                    if i + horizons[j] < n_barres:
                        m = cote * (C[d, i + horizons[j]] - prix)
                        markout[d, j, 0] += m
                        markout[d, j, 1] += m * m
                        markout[d, j, 2] += 1.0
            inv += q * (C[d, i] - ref)
            q_max = max(q_max, abs(q))
        liquidation = abs(q) * p[I_HLIQ]
        sortie[d, O_PNL] = capture + inv - liquidation - frais_tot
        sortie[d, O_CAPTURE] = capture
        sortie[d, O_INVENTAIRE] = inv
        sortie[d, O_LIQUIDATION] = liquidation
        sortie[d, O_FRAIS] = frais_tot
        sortie[d, O_QMAX] = q_max
        sortie[d, O_NEXEC] = n_exec
        sortie[d, O_QFINAL] = q
        sortie[d, O_PNL_CASH] = cash + q * C[d, n_barres - 1] - liquidation


def rejouer(jours, strategie, marche, seuil=0.1, f=0.5, graine=20260714, deux_cotes=False, detail=False):
    """Résultats (n_jours, N_OUT) d'une stratégie. `ub`/`ua` (file d'attente) et `wb`/`wa` (placebo) ne dépendent pas des prix.

    detail=True renvoie aussi le markout (n_jours, n_horizons, 3 = somme, somme des carrés, effectif)
    et les cotes posées, pour le test anti-fuite.
    """
    n_jours, n_barres = jours["C"].shape
    rng = np.random.default_rng(graine)
    ub, ua, wb, wa = (rng.random((n_jours, n_barres)) for _ in range(4))
    # translation par jour : les profondeurs sont relatives, et des prix proches de 0 gardent la comptabilité exacte à 1e-12
    decalage = jours["C"][:, :1]
    sortie = np.zeros((n_jours, N_OUT))
    markout = np.zeros((n_jours, len(HORIZONS_MARKOUT), 3))
    cote_bid, cote_ask = np.full((n_jours, n_barres), np.nan), np.full((n_jours, n_barres), np.nan)
    _rejouer(jours["H"] - decalage, jours["L"] - decalage, jours["C"] - decalage, jours["valide"], ub, ua, wb, wa,
             construire_params(strategie, marche), f, seuil, deux_cotes, np.array(HORIZONS_MARKOUT, dtype=np.int64),
             sortie, markout, cote_bid, cote_ask)
    return (sortie, markout, cote_bid + decalage, cote_ask + decalage) if detail else sortie


def resume_markout(markout):
    """Markout moyen par exécution (pips) et son erreur standard, par horizon."""
    somme, somme2, n = markout[:, :, 0].sum(0), markout[:, :, 1].sum(0), markout[:, :, 2].sum(0)
    moyenne = somme / np.maximum(n, 1)
    variance = np.maximum(somme2 / np.maximum(n, 1) - moyenne ** 2, 0.0)
    return {f"{h}min": {"moyenne_pips": float(m), "erreur_standard": float(np.sqrt(v / max(c, 1))), "n_executions": int(c)}
            for h, m, v, c in zip(HORIZONS_MARKOUT, moyenne, variance, n)}


def sensibilite_rejeu(jours, strategies, marche, fs, seuils, graine=20260714, deux_cotes=False):
    """Sharpe annualisé (len(seuils), len(fs), n_strategies). Mêmes tirages partout : seuls f et le seuil changent."""
    from .monte_carlo import sharpe_annualise  # import local : monte_carlo n'a pas besoin du rejeu
    out = np.zeros((len(seuils), len(fs), len(strategies)))
    for a, seuil in enumerate(seuils):
        for b, f in enumerate(fs):
            for j, s in enumerate(strategies):
                out[a, b, j] = sharpe_annualise(rejouer(jours, s, marche, seuil, f, graine, deux_cotes)[:, O_PNL])
    return out


def comparer_placebo_rejeu(jours, strategie, placebo, marche, seuil, f, graines, deux_cotes=False):
    """{"ref"|"placebo": (Sharpe par graine, PnL moyen/jour par graine)} sur les mêmes graines.

    Le PnL moyen est indispensable : quand l'espérance est négative, réduire la variance DÉGRADE le Sharpe.
    """
    from .monte_carlo import sharpe_annualise
    sortie = {}
    for nom, s in (("ref", strategie), ("placebo", placebo)):
        pnl = [rejouer(jours, s, marche, seuil, f, g, deux_cotes)[:, O_PNL] for g in graines]
        sortie[nom] = (np.array([sharpe_annualise(x) for x in pnl]), np.array([x.mean() for x in pnl]))
    return sortie
