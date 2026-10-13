"""Calibration : sigma mesuré sur TRAIN ; tout le reste (A, k, spread, sélection adverse) = hypothèses.

On n'a PAS de données d'ordres : A et k (intensité d'exécution lambda = A exp(-k delta)), la part
de flux informé p et le saut alpha ne se mesurent pas sur des barres 1-minute. Ce sont des
hypothèses explicites, fixées a priori, dont on mesure ensuite la sensibilité (grille 3x3).
"""
from dataclasses import dataclass

import numpy as np

from .donnees import ANNEE_TRAIN_FIN, charger_annee

SESSION_LONDRES = (3, 12)  # heures de New York des données (= 8h-17h Londres toute l'année, sauf ~3 semaines de décalage des heures d'été)


def sigma_par_heure(annees=range(2010, ANNEE_TRAIN_FIN + 1)):
    """Vol réalisée par heure de New York, en pips/sqrt(s), sur TRAIN uniquement.

    Écart quadratique moyen des variations de close d'une minute à la suivante (minutes
    consécutives seulement : on exclut les trous et les week-ends), divisé par sqrt(60).
    """
    if max(annees) > ANNEE_TRAIN_FIN:
        raise ValueError("La calibration n'utilise que TRAIN (<= 2018).")
    somme, nb = np.zeros(24), np.zeros(24)
    for annee in annees:
        barres = charger_annee(annee)
        s, n = _somme_carres_par_heure(barres["close"].to_numpy(), barres.index)
        somme += s
        nb += n
    return np.sqrt(somme / np.maximum(nb, 1) / 60.0)


def _somme_carres_par_heure(close, index):
    consecutives = np.diff(index.values).astype("timedelta64[s]").astype(int) == 60
    r = np.diff(close)[consecutives]
    heures = index.hour.to_numpy()[1:][consecutives]
    return np.bincount(heures, weights=r * r, minlength=24), np.bincount(heures, minlength=24).astype(float)


def sigma_session(sigma_h, session=SESSION_LONDRES):
    """Moyenne en VARIANCE sur les heures de la session (les variances s'additionnent, pas les écarts-types)."""
    h0, h1 = session
    return float(np.sqrt(np.mean(sigma_h[h0:h1] ** 2)))


@dataclass(frozen=True)
class Hypotheses:
    """Valeurs de base, documentées dans le README. Aucune n'est mesurée sur des données d'ordres."""

    A: float = 0.1                # exécutions/s/côté à profondeur nulle -> ~2 300 exécutions par session de 9 h
    k: float = 6.0                # 1/pip : l'intensité est divisée par e quand on s'éloigne de 0,17 pip
    demi_spread_marche: float = 0.1   # pip : EURUSD interbancaire ≈ 0,1-0,3 pip de spread, soit ≈ 0,1 de demi-spread
    p_adverse: float = 0.2        # 1 exécution sur 5 est suivie d'un saut contre le market maker
    alpha: float = 0.3            # pip
    frais: float = 0.005          # pip/exécution (≈ 0,5 USD par million) : ordre de grandeur, non vérifié
    Q: int = 20                   # lots
    latence_pas: int = 1          # recalcul des cotes à chaque pas de temps (dt = 0,1 s dans le run principal)


def grille_sensibilite_Ak(h=Hypotheses()):
    """Grille 3x3 (robustesse, pas optimisation) autour des hypothèses : A et k du MARCHÉ varient, la stratégie garde ses croyances."""
    return [h.A / 2, h.A, h.A * 2], [h.k * 2 / 3, h.k, h.k * 1.5]
