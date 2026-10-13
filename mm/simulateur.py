"""Simulateur de market making sur une session (mid brownien arithmétique + exécutions de Poisson).

Unités : pips, secondes, lots. Le mid part de 0 (seuls les écarts comptent).

Déroulé d'un pas de temps t (dt secondes) :
  1. toutes les `latence_pas` périodes, les cotes (prix absolus) sont recalculées depuis le mid courant ;
  2. exécution côté bid puis côté ask : probabilité 1-exp(-lambda*dt), lambda = A*exp(-k*profondeur),
     la profondeur étant mesurée au mid COURANT (donc une cote périmée est mal placée) ;
  3. sélection adverse : après une exécution, avec probabilité p le mid saute de alpha contre nous ;
  4. diffusion du mid : dS = sigma*sqrt(dt)*N(0,1).

Tous les nombres aléatoires sont tirés AVANT (numpy default_rng) et passés au noyau numba :
la reproductibilité est celle de numpy, et deux stratégies peuvent consommer exactement les
mêmes tirages (nombres aléatoires communs).
"""
import math
from dataclasses import dataclass

import numpy as np
from numba import njit, prange

from .modeles import profondeurs_strategie

# indices du vecteur de paramètres (une ligne = une stratégie dans un marché)
(I_CODE, I_GAMMA, I_SIG_MOD, I_K_MOD, I_A_MOD, I_DEMI_NAIF, I_CAP, I_Q, I_L,
 I_SIG, I_A, I_K, I_PADV, I_ALPHA, I_HLIQ, I_FRAIS, I_DT, N_PARAMS) = range(18)

# indices des sorties d'une session
(O_PNL, O_CAPTURE, O_INVENTAIRE, O_SEL_ADV, O_LIQUIDATION, O_FRAIS, O_QMAX,
 O_NEXEC, O_QFINAL, O_PNL_CASH, N_OUT) = range(11)
NOMS_SORTIES = ["pnl", "capture", "inventaire", "dont_selection_adverse", "cout_liquidation",
                "frais", "inventaire_max", "n_executions", "inventaire_final", "pnl_par_cash"]


@dataclass(frozen=True)
class Marche:
    """Le monde simulé (vrais paramètres, inconnus de la stratégie)."""

    sigma: float                 # pips / sqrt(s)
    A: float                     # exécutions / s à profondeur nulle, par côté
    k: float                     # 1/pip
    p_adverse: float             # proba qu'une exécution soit suivie d'un saut contre nous
    alpha: float                 # taille du saut (pips)
    demi_spread_liq: float       # demi-spread de marché payé à la liquidation (pips)
    frais: float                 # pips / exécution (positif = coût, négatif = rebate)
    dt: float = 1.0              # s
    duree: float = 9 * 3600.0    # s : session de Londres 3h-12h (heure de New York)

    @property
    def n_pas(self):
        return int(round(self.duree / self.dt))


def construire_params(strategie, marche):
    p = np.zeros(N_PARAMS)
    p[I_CODE], p[I_GAMMA] = strategie.code, strategie.gamma
    p[I_SIG_MOD], p[I_K_MOD], p[I_A_MOD] = strategie.sigma, strategie.k, strategie.A
    p[I_DEMI_NAIF], p[I_CAP], p[I_Q], p[I_L] = strategie.demi_naif, strategie.cap, strategie.Q, strategie.latence_pas
    p[I_SIG], p[I_A], p[I_K] = marche.sigma, marche.A, marche.k
    p[I_PADV], p[I_ALPHA], p[I_HLIQ], p[I_FRAIS], p[I_DT] = (
        marche.p_adverse, marche.alpha, marche.demi_spread_liq, marche.frais, marche.dt)
    return p


def tirages(graine, indice_session, n_pas):
    """Tirages d'une session : mêmes (graine, indice) => mêmes nombres, quelle que soit la stratégie."""
    rng = np.random.default_rng([graine, indice_session])
    z = rng.standard_normal(n_pas)
    # exécution bid, exécution ask, saut après bid, saut après ask, profondeurs du placebo (bid, ask)
    u = rng.random((6, n_pas))
    return z, u[0], u[1], u[2], u[3], u[4], u[5]


@njit(cache=True)
def _session(p, z, ub, ua, vb, va, wb, wa, sortie, trace, t_mid, t_bid, t_ask, t_q, t_fill):
    n = z.shape[0]
    dt, sig, A, k = p[I_DT], p[I_SIG], p[I_A], p[I_K]
    p_adv, alpha, frais, borne = p[I_PADV], p[I_ALPHA], p[I_FRAIS], p[I_Q]
    pas_maj = max(int(p[I_L]), 1)
    pas_vol = sig * math.sqrt(dt)

    s = 0.0
    q = 0.0
    cash = 0.0
    capture = inv_diff = sel_adv = frais_tot = 0.0
    q_max = 0.0
    n_exec = 0
    cote_bid = cote_ask = 0.0

    for t in range(n):
        if t % pas_maj == 0:
            tau = (n - t) * dt
            db, da = profondeurs_strategie(int(p[I_CODE]), q, tau, p[I_GAMMA], p[I_SIG_MOD],
                                           p[I_K_MOD], p[I_A_MOD], p[I_DEMI_NAIF], p[I_CAP], wb[t], wa[t])
            # une cote ne passe jamais du mauvais côté du mid : lambda(delta) n'est valable que pour delta >= 0
            cote_bid = s - max(db, 0.0)
            cote_ask = s + max(da, 0.0)
        rempli = 0

        if q < borne:  # la borne d'inventaire est un contrôle de risque au moment de l'exécution
            prof = max(s - cote_bid, 0.0)
            if ub[t] < 1.0 - math.exp(-A * math.exp(-k * prof) * dt):
                q += 1.0
                cash -= cote_bid + frais
                capture += s - cote_bid
                frais_tot += frais
                n_exec += 1
                rempli += 1
                if vb[t] < p_adv:
                    s -= alpha
                    sel_adv -= q * alpha
        if q > -borne:
            prof = max(cote_ask - s, 0.0)
            if ua[t] < 1.0 - math.exp(-A * math.exp(-k * prof) * dt):
                q -= 1.0
                cash += cote_ask - frais
                capture += cote_ask - s
                frais_tot += frais
                n_exec += 1
                rempli += 2
                if va[t] < p_adv:
                    s += alpha
                    sel_adv += q * alpha

        ds = pas_vol * z[t]
        inv_diff += q * ds
        if trace:
            t_mid[t], t_bid[t], t_ask[t], t_q[t], t_fill[t] = s, cote_bid, cote_ask, q, rempli
        s += ds
        q_max = max(q_max, abs(q))

    liquidation = abs(q) * p[I_HLIQ]
    sortie[O_PNL] = capture + inv_diff + sel_adv - liquidation - frais_tot
    sortie[O_CAPTURE] = capture
    sortie[O_INVENTAIRE] = inv_diff + sel_adv
    sortie[O_SEL_ADV] = sel_adv
    sortie[O_LIQUIDATION] = liquidation
    sortie[O_FRAIS] = frais_tot
    sortie[O_QMAX] = q_max
    sortie[O_NEXEC] = n_exec
    sortie[O_QFINAL] = q
    sortie[O_PNL_CASH] = cash + q * s - liquidation  # contrôle indépendant de la décomposition


@njit(parallel=True, cache=True)
def _lot(params, z, ub, ua, vb, va, wb, wa):
    """Une ligne de `params` par stratégie/cellule, mêmes tirages pour toutes (parallèle sur les lignes)."""
    sortie = np.zeros((params.shape[0], N_OUT))
    vide = np.zeros(0)
    vide_i = np.zeros(0, dtype=np.int64)
    for i in prange(params.shape[0]):
        _session(params[i], z, ub, ua, vb, va, wb, wa, sortie[i], False, vide, vide, vide, vide, vide_i)
    return sortie


def simuler_matrice(params, n_sessions, graine, n_pas):
    """Résultats (n_lignes, n_sessions, N_OUT) : la session s utilise les tirages (graine, s) pour TOUTES les lignes."""
    params = np.atleast_2d(np.asarray(params, dtype=np.float64))
    res = np.empty((params.shape[0], n_sessions, N_OUT))
    for s in range(n_sessions):
        res[:, s, :] = _lot(params, *tirages(graine, s, n_pas))
    return res


def simuler_session(strategie, marche, graine=0, indice=0):
    """Une session, sorties nommées (pratique pour les tests et le notebook)."""
    brut = _lot(construire_params(strategie, marche)[None, :], *tirages(graine, indice, marche.n_pas))[0]
    return dict(zip(NOMS_SORTIES, brut))


def simuler_trajectoire(strategie, marche, graine=0, indice=0):
    """Une session avec enregistrement pas à pas : mid, cotes, inventaire, exécutions (1=bid, 2=ask, 3=les deux)."""
    n = marche.n_pas
    t_mid, t_bid, t_ask, t_q = (np.zeros(n) for _ in range(4))
    t_fill = np.zeros(n, dtype=np.int64)
    sortie = np.zeros(N_OUT)
    _session(construire_params(strategie, marche), *tirages(graine, indice, n), sortie, True,
             t_mid, t_bid, t_ask, t_q, t_fill)
    return dict(temps=np.arange(n) * marche.dt, mid=t_mid, bid=t_bid, ask=t_ask, inventaire=t_q,
                executions=t_fill, sortie=dict(zip(NOMS_SORTIES, sortie)))
