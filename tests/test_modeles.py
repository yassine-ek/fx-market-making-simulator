import math

import pytest

from mm.modeles import (Strategie, constantes_glft, gamma_pour_skew_cible, jeu_strategies_base, prix_reservation,
                        profondeurs_as, profondeurs_as_plafonne, profondeurs_glft, profondeurs_naif,
                        profondeurs_placebo, spread_total_as)

SIGMA, K, A, TAU = 0.33, 6.0, 0.1, 32400.0


def test_prix_reservation_egal_au_mid_sans_inventaire():
    assert prix_reservation(1.2345, 0, 1e-4, SIGMA, TAU) == 1.2345


def test_prix_reservation_decale_contre_linventaire():
    assert prix_reservation(0.0, 5, 1e-4, SIGMA, TAU) < 0.0 < prix_reservation(0.0, -5, 1e-4, SIGMA, TAU)


def test_spread_as_croit_avec_gamma_et_sigma():
    gammas = [1e-6, 1e-5, 1e-4, 1e-3]
    spreads = [spread_total_as(g, SIGMA, K, TAU) for g in gammas]
    assert spreads == sorted(spreads) and spreads[0] < spreads[-1]
    sigmas = [0.1, 0.2, 0.4]
    par_sigma = [spread_total_as(1e-4, s, K, TAU) for s in sigmas]
    assert par_sigma == sorted(par_sigma) and par_sigma[0] < par_sigma[-1]


def test_spread_as_limite_risque_neutre():
    assert spread_total_as(0.0, SIGMA, K, TAU) == pytest.approx(2.0 / K)
    assert spread_total_as(1e-9, SIGMA, K, 0.0) == pytest.approx(2.0 / K, rel=1e-6)


def test_profondeurs_as_symetriques_sans_inventaire_et_somme_egale_au_spread():
    db, da = profondeurs_as(0, 1e-4, SIGMA, K, TAU)
    assert db == pytest.approx(da)
    db, da = profondeurs_as(7, 1e-4, SIGMA, K, TAU)
    assert db + da == pytest.approx(spread_total_as(1e-4, SIGMA, K, TAU))
    assert db > da  # long : on cote le bid loin, l'ask près


def test_as_plafonne_borne_le_decalage_et_colle_a_as_en_dessous_du_plafond():
    cap = 0.05
    db, da = profondeurs_as_plafonne(1000, 1e-4, SIGMA, K, TAU, cap)
    assert (db - da) / 2 == pytest.approx(cap)
    assert profondeurs_as_plafonne(1, 1e-6, SIGMA, K, TAU, cap) == pytest.approx(profondeurs_as(1, 1e-6, SIGMA, K, TAU))


def test_glft_antisymetrie_et_pente():
    g = 0.01
    c1, c2 = constantes_glft(g, SIGMA, A, K)
    db0, da0 = profondeurs_glft(0, g, SIGMA, A, K)
    assert db0 == pytest.approx(da0)
    db3, da3 = profondeurs_glft(3, g, SIGMA, A, K)
    dbm3, dam3 = profondeurs_glft(-3, g, SIGMA, A, K)
    assert db3 == pytest.approx(dam3) and da3 == pytest.approx(dbm3)
    assert profondeurs_glft(4, g, SIGMA, A, K)[0] - db3 == pytest.approx(c2)
    assert c1 == pytest.approx(math.log(1 + g / K) / g)


def test_glft_c1_tend_vers_1_sur_k_quand_gamma_tend_vers_zero():
    assert constantes_glft(1e-9, SIGMA, A, K)[0] == pytest.approx(1.0 / K, rel=1e-6)


def test_naif_ignore_linventaire():
    assert profondeurs_naif(0.2) == (0.2, 0.2)


def test_placebo_borne_et_moyenne():
    assert profondeurs_placebo(0.2, 0.5, 1.0) == pytest.approx((0.2, 0.4))
    assert profondeurs_placebo(0.2, 0.0, 0.0) == (0.0, 0.0)


@pytest.mark.parametrize("modele", ["as", "glft"])
def test_gamma_pour_skew_cible_inverse_bien(modele):
    g = gamma_pour_skew_cible(modele, 0.1, 10.0, SIGMA, A, K, TAU)
    if modele == "as":
        assert 10.0 * g * SIGMA ** 2 * TAU / 2 == pytest.approx(0.1)
    else:
        assert 10.0 * constantes_glft(g, SIGMA, A, K)[1] == pytest.approx(0.1)


def test_jeu_strategies_base_meme_agressivite_pas_meme_gamma():
    naif, as_, plafonne, glft = jeu_strategies_base(SIGMA, A, K, 20, TAU)
    assert naif.gamma == 0 and as_.gamma == plafonne.gamma and glft.gamma > 100 * as_.gamma
    assert isinstance(naif, Strategie) and plafonne.cap < 1.0 / K
