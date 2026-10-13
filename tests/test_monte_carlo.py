from dataclasses import replace

import numpy as np
import pytest

from mm.modeles import jeu_strategies_base, strategie_placebo
from mm.monte_carlo import (cvar, ic_bootstrap_blocs, ic_bootstrap_sharpe, monte_carlo, resumer, sharpe_annualise)
from mm.simulateur import Marche, O_PNL

MARCHE = Marche(sigma=0.33, A=0.5, k=3.0, p_adverse=0.1, alpha=0.3, demi_spread_liq=0.1, frais=0.0,
                dt=1.0, duree=1800.0)


def test_sharpe_annualise_valeur_connue():
    pnl = np.array([1.0, 3.0] * 50)  # moyenne 2, écart-type empirique 1,005...
    assert sharpe_annualise(pnl) == pytest.approx(2 / pnl.std(ddof=1) * np.sqrt(252))
    assert np.isnan(sharpe_annualise(np.ones(10)))


def test_cvar_moyenne_des_pires_cas():
    pnl = np.arange(100.0)
    assert cvar(pnl, 0.05) == pytest.approx(np.mean([0, 1, 2, 3, 4]))


def test_ic_bootstrap_contient_lestimation_et_se_resserre_avec_n():
    rng = np.random.default_rng(0)
    petit, grand = rng.normal(1, 5, 100), rng.normal(1, 5, 2000)
    for x in (petit, grand):
        bas, haut = ic_bootstrap_sharpe(x)
        assert bas < sharpe_annualise(x) < haut
    assert np.subtract(*ic_bootstrap_sharpe(grand)[::-1]) < np.subtract(*ic_bootstrap_sharpe(petit)[::-1])


def test_bootstrap_par_blocs_plus_large_quand_les_pnl_sont_autocorrelés():
    rng = np.random.default_rng(1)
    x = np.zeros(1000)
    for t in range(1, 1000):  # AR(1) rho = 0,9 : des régimes, comme la volatilité réelle
        x[t] = 0.9 * x[t - 1] + rng.standard_normal()
    x += 0.2
    largeur_iid = np.subtract(*ic_bootstrap_sharpe(x)[::-1])
    largeur_blocs = np.subtract(*ic_bootstrap_blocs(x, bloc=20)[::-1])
    assert largeur_blocs > 1.5 * largeur_iid


def test_monte_carlo_nombres_aleatoires_communs_et_reproductible():
    strategies = jeu_strategies_base(0.33, 0.5, 3.0, 10, MARCHE.duree)
    a = monte_carlo(strategies, MARCHE, 6, graine=5)
    b = monte_carlo(strategies, MARCHE, 6, graine=5)
    assert np.array_equal(a, b)
    deux_fois_la_meme = monte_carlo([strategies[1], strategies[1]], MARCHE, 6, graine=5)
    assert np.array_equal(deux_fois_la_meme[0], deux_fois_la_meme[1])  # mêmes sessions pour toutes les lignes


def test_resumer_champs_et_coherence():
    strategies = jeu_strategies_base(0.33, 0.5, 3.0, 10, MARCHE.duree)
    r = resumer(monte_carlo(strategies, MARCHE, 40, graine=2)[1])
    pnl_cvar, pnl_moyen = r["cvar_5pct"], r["pnl_moyen_pips_lot"]
    assert pnl_cvar <= pnl_moyen and 0 <= r["proba_perte"] <= 1 and r["inventaire_max_moyen"] <= 10
    d = r["decomposition_moyenne"]
    assert sum(d["capture_spread"] + d["inventaire_total"] + d["cout_liquidation"] + d["frais"] for _ in [0]) == pytest.approx(pnl_moyen)
    assert r["sharpe_ic95"][0] < r["sharpe_annualise"] < r["sharpe_ic95"][1]


def test_placebo_est_battu_par_le_controle_dinventaire_dans_le_monde_simule():
    marche = replace(MARCHE, duree=3600.0)
    base = jeu_strategies_base(0.33, 0.5, 3.0, 10, marche.duree)
    jeu = [base[1], strategie_placebo(base[1], 0.5 * 2 / 3.0)]
    pnl = monte_carlo(jeu, marche, 60, graine=3)[:, :, O_PNL]
    assert pnl[0].std() < pnl[1].std()  # AS réduit le risque d'inventaire par rapport à des cotes sans logique
