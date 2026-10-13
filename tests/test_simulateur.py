from dataclasses import replace

import numpy as np
import pytest

from mm.modeles import Strategie, jeu_strategies_base, strategie_placebo
from mm.simulateur import (Marche, O_CAPTURE, O_INVENTAIRE, O_LIQUIDATION, O_FRAIS, O_NEXEC, O_PNL, O_PNL_CASH, O_QMAX,
                           construire_params, simuler_matrice, simuler_session, simuler_trajectoire, tirages)

MARCHE = Marche(sigma=0.33, A=0.5, k=3.0, p_adverse=0.0, alpha=0.3, demi_spread_liq=0.1, frais=0.0,
                dt=1.0, duree=3600.0)


def naif(demi=0.2, Q=10 ** 6, **kw):
    return Strategie("naif", "naif", 0.0, sigma=0.33, k=3.0, A=0.5, demi_naif=demi, cap=0.1, Q=Q, **kw)


def test_sigma_nul_sans_selection_adverse_pnl_egal_capture_de_spread_exacte():
    marche = replace(MARCHE, sigma=0.0)
    for indice in range(5):
        r = simuler_session(naif(0.2), marche, graine=1, indice=indice)
        assert r["inventaire"] == 0.0 and r["frais"] == 0.0
        assert r["capture"] == pytest.approx(0.2 * r["n_executions"], abs=1e-9)
        assert r["pnl"] == pytest.approx(0.2 * r["n_executions"] - 0.1 * abs(r["inventaire_final"]), abs=1e-9)


def test_sigma_nul_nombre_dexecutions_conforme_a_la_theorie_de_poisson():
    marche = replace(MARCHE, sigma=0.0)
    res = simuler_matrice(construire_params(naif(0.2), marche), 150, 3, marche.n_pas)[0]
    p_pas = 1.0 - np.exp(-marche.A * np.exp(-marche.k * 0.2) * marche.dt)
    attendu = 2 * marche.n_pas * p_pas
    sigma_mc = np.sqrt(2 * marche.n_pas * p_pas * (1 - p_pas) / 150)
    assert abs(res[:, O_NEXEC].mean() - attendu) < 4 * sigma_mc


def test_inventaire_borne_et_borne_atteinte():
    marche = replace(MARCHE, A=2.0)
    res = simuler_matrice(construire_params(naif(0.05, Q=5), marche), 20, 5, marche.n_pas)[0]
    assert res[:, O_QMAX].max() == 5  # test non vide : la borne est bien touchée
    t = simuler_trajectoire(naif(0.05, Q=5), marche, 5, 0)
    assert np.abs(t["inventaire"]).max() <= 5


def test_reproductibilite_par_graine():
    s = jeu_strategies_base(0.33, 0.5, 3.0, 10, 3600.0)[1]
    marche = replace(MARCHE, p_adverse=0.2)
    assert simuler_session(s, marche, 7, 3) == simuler_session(s, marche, 7, 3)
    assert simuler_session(s, marche, 7, 3) != simuler_session(s, marche, 8, 3)
    assert all((a == b).all() for a, b in zip(tirages(7, 3, 100), tirages(7, 3, 100)))


def test_identite_comptable_pnl_egal_cash_plus_inventaire_a_1e_9():
    """PnL = capture + inventaire - liquidation - frais, ET égal à cash + q*mid - liquidation (calcul indépendant)."""
    marche = replace(MARCHE, p_adverse=0.3, frais=0.01)
    strategies = jeu_strategies_base(0.33, 0.5, 3.0, 8, 3600.0, latence_pas=3)
    strategies.append(strategie_placebo(strategies[1], 0.3))
    res = simuler_matrice(np.array([construire_params(s, marche) for s in strategies]), 20, 11, marche.n_pas)
    somme = res[..., O_CAPTURE] + res[..., O_INVENTAIRE] - res[..., O_LIQUIDATION] - res[..., O_FRAIS]
    assert np.abs(res[..., O_PNL] - somme).max() < 1e-9
    assert np.abs(res[..., O_PNL] - res[..., O_PNL_CASH]).max() < 1e-9


def test_latence_les_cotes_ne_changent_que_toutes_les_L_periodes():
    L = 7
    t = simuler_trajectoire(jeu_strategies_base(0.33, 0.5, 3.0, 10, 3600.0, latence_pas=L)[1], MARCHE, 2, 0)
    change = np.flatnonzero(np.diff(t["bid"]) != 0) + 1
    assert len(change) > 10 and (change % L == 0).all()


def test_selection_adverse_degrade_le_pnl_a_tirages_communs():
    s = naif(0.2, Q=20)
    p0, p1 = (simuler_matrice(construire_params(s, replace(MARCHE, p_adverse=p)), 30, 4, MARCHE.n_pas)[0, :, O_PNL]
              for p in (0.0, 1.0))
    assert p1.mean() < p0.mean() - 100


def test_placebo_profondeur_moyenne_egale_a_la_cible():
    marche = replace(MARCHE, sigma=0.0)
    placebo = strategie_placebo(naif(), 0.15)
    t = simuler_trajectoire(placebo, marche, 9, 0)
    assert np.mean(t["mid"] - t["bid"]) == pytest.approx(0.15, rel=0.05)
    assert np.mean(t["ask"] - t["mid"]) == pytest.approx(0.15, rel=0.05)


def test_cotes_jamais_du_mauvais_cote_du_mid_au_moment_de_la_mise_a_jour():
    t = simuler_trajectoire(jeu_strategies_base(0.33, 0.5, 3.0, 40, 3600.0)[1], MARCHE, 6, 0)  # AS, Q grand : skew fort
    assert (t["bid"] <= t["mid"] + 1e-12).all() and (t["ask"] >= t["mid"] - 1e-12).all()
