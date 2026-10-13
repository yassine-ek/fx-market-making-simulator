import numpy as np
import pytest

from mm.significativite import EULER_MASCHERONI, dsr, psr, sharpe_quotidien, sharpe_reference_dsr


def echantillon(moyenne, n=2000, graine=0):
    return np.random.default_rng(graine).normal(moyenne, 1.0, n)


def test_psr_vaut_un_demi_pour_un_sharpe_nul_et_suit_le_signe():
    x = echantillon(0.0, n=20000)
    x = x - x.mean()  # Sharpe exactement nul
    assert psr(x, 0.0) == pytest.approx(0.5, abs=1e-6)
    assert psr(echantillon(0.1), 0.0) > 0.99
    assert psr(echantillon(-0.1), 0.0) < 0.01


def test_psr_decroit_avec_le_sharpe_de_reference():
    x = echantillon(0.05)
    assert psr(x, 0.0) > psr(x, 0.03) > psr(x, 0.08)


def test_sharpe_de_reference_dsr_valeurs_connues():
    assert sharpe_reference_dsr([0.1]) == 0.0                      # un seul essai : rien à déflater
    # N = 2 : Phi^-1(1 - 1/2) = 0, donc SR0 = sqrt(var) * gamma * Phi^-1(1 - 1/(2e)) avec Phi^-1(0,8161) = 0,90045
    assert sharpe_reference_dsr([0.0, 1.0]) == pytest.approx(np.sqrt(0.5) * EULER_MASCHERONI * 0.9004526, rel=1e-6)
    rng = np.random.default_rng(1)
    z = rng.normal(0.0, 0.05, 300)
    assert sharpe_reference_dsr(z[:10]) < sharpe_reference_dsr(z[:100]) < sharpe_reference_dsr(z)  # plus d'essais, plus de chance


def test_dsr_est_inferieur_au_psr_quand_les_essais_dispersent():
    x = echantillon(0.06)
    essais = np.random.default_rng(2).normal(0.0, 0.05, 30)
    assert 0.0 <= dsr(x, essais) < psr(x, 0.0) <= 1.0


def test_un_sharpe_negatif_a_un_dsr_nul():
    x = echantillon(-0.05)
    essais = np.array([sharpe_quotidien(echantillon(-0.05, graine=g)) for g in range(30)])
    assert dsr(x, essais) < 1e-3
