import numpy as np
import pandas as pd
import pytest

from mm.calibration import _somme_carres_par_heure, grille_sensibilite_Ak, sigma_par_heure, sigma_session
from mm.donnees import charger_annee


def barres_synthetiques(sigma_par_h, jours=60, graine=0, trous=0.0):
    """Marche aléatoire 1 min dont le sigma (pips/sqrt(s)) vaut sigma_par_h[heure]."""
    index = pd.date_range("2018-01-02", periods=jours * 1440, freq="min")
    rng = np.random.default_rng(graine)
    sig = np.array([sigma_par_h[h] for h in index.hour]) * np.sqrt(60)
    close = 11000 + np.cumsum(rng.standard_normal(len(index)) * sig)
    garde = rng.random(len(index)) >= trous
    return close[garde], index[garde]


def test_sigma_retrouve_a_quelques_pourcents_par_heure():
    vrai = np.where(np.arange(24) < 12, 0.1, 0.3)
    close, index = barres_synthetiques(vrai)
    somme, n = _somme_carres_par_heure(close, index)
    estime = np.sqrt(somme / n / 60)
    assert np.abs(estime / vrai - 1).max() < 0.06


def test_les_trous_ne_fabriquent_pas_de_volatilite():
    vrai = np.full(24, 0.2)
    close, index = barres_synthetiques(vrai, trous=0.3)  # 30 % de minutes manquantes
    somme, n = _somme_carres_par_heure(close, index)
    assert np.abs(np.sqrt(somme / n / 60) / 0.2 - 1).max() < 0.1  # sans filtre des minutes consécutives : ~ +50 %


def test_sigma_session_moyenne_les_variances():
    sigma_h = np.zeros(24)
    sigma_h[3:12] = np.where(np.arange(3, 12) % 2 == 0, 0.1, 0.3)
    assert sigma_session(sigma_h) == pytest.approx(np.sqrt(np.mean(sigma_h[3:12] ** 2)))


def test_le_test_2023_est_scelle():
    with pytest.raises(PermissionError):
        charger_annee(2023)
    with pytest.raises(PermissionError):
        charger_annee(2025)
    with pytest.raises(ValueError):
        sigma_par_heure(range(2017, 2020))


def test_grille_de_sensibilite_A_k_reste_grossiere():
    valeurs_A, valeurs_k = grille_sensibilite_Ak()
    assert len(valeurs_A) <= 3 and len(valeurs_k) <= 3
