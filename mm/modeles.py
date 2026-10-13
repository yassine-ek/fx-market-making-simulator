"""Modèles de cotation d'un market maker.

Unités partout : prix en pips, temps en secondes, inventaire en lots (1 lot = 1 M EUR,
donc 1 pip x 1 lot = 100 USD). Les fonctions retournent des PROFONDEURS (distance de
chaque cote au mid, en pips), pas des prix : c'est ce que le simulateur consomme.

Les fonctions sont compilées numba pour pouvoir être appelées dans la boucle du
simulateur, mais restent appelables telles quelles depuis Python (tests, notebook).
"""
import math
from dataclasses import dataclass, replace

from numba import njit
from scipy.optimize import brentq

CODE_NAIF, CODE_AS, CODE_AS_PLAFONNE, CODE_GLFT, CODE_PLACEBO = 0, 1, 2, 3, 4
CODES = {"naif": CODE_NAIF, "as": CODE_AS, "as_plafonne": CODE_AS_PLAFONNE, "glft": CODE_GLFT,
         "placebo": CODE_PLACEBO}


# ---------------------------------------------------------------- Avellaneda-Stoikov (2008)
@njit(cache=True)
def prix_reservation(s, q, gamma, sigma, tau):
    """r = s - q * gamma * sigma^2 * (T - t) : le mid « corrigé » du risque d'inventaire."""
    return s - q * gamma * sigma * sigma * tau


@njit(cache=True)
def spread_total_as(gamma, sigma, k, tau):
    """Spread optimal gamma*sigma^2*(T-t) + (2/gamma)*ln(1+gamma/k).

    Quand gamma -> 0 le second terme tend vers 2/k (limite risque-neutre) : on la
    prend explicitement pour éviter la division 0/0.
    """
    if gamma < 1e-12:
        return 2.0 / k
    return gamma * sigma * sigma * tau + (2.0 / gamma) * math.log1p(gamma / k)


@njit(cache=True)
def profondeurs_as(q, gamma, sigma, k, tau):
    """(profondeur bid, profondeur ask) : cotes symétriques autour de r, donc décalées autour de s."""
    demi = 0.5 * spread_total_as(gamma, sigma, k, tau)
    decalage = q * gamma * sigma * sigma * tau  # s - r : positif si on est long
    return demi + decalage, demi - decalage


@njit(cache=True)
def profondeurs_as_plafonne(q, gamma, sigma, k, tau, cap):
    """AS dont le décalage d'inventaire est borné par `cap` pips.

    Sans plafond, un gros inventaire envoie une cote de l'autre côté du mid (profondeur
    négative) : le modèle extrapole alors lambda(delta) hors de son domaine de validité.
    """
    demi = 0.5 * spread_total_as(gamma, sigma, k, tau)
    decalage = q * gamma * sigma * sigma * tau
    decalage = min(max(decalage, -cap), cap)
    return demi + decalage, demi - decalage


# ---------------------------------------------------------------- Guéant-Lehalle-Fernandez-Tapia (2013)
@njit(cache=True)
def constantes_glft(gamma, sigma, A, k):
    """c1, c2 de l'approximation asymptotique (horizon long), taille d'ordre = 1 lot.

    c1 = (1/gamma) ln(1+gamma/k)                      : demi-spread de base
    c2 = sqrt( gamma sigma^2/(2Ak) (1+gamma/k)^(1+k/gamma) ) : pente d'inventaire (pips/lot)
    """
    c1 = math.log1p(gamma / k) / gamma
    # exp(ln(.)) plutôt que ** : évite le dépassement quand gamma est très petit
    puissance = math.exp((1.0 + k / gamma) * math.log1p(gamma / k))
    c2 = math.sqrt(gamma * sigma * sigma / (2.0 * A * k) * puissance)
    return c1, c2


@njit(cache=True)
def profondeurs_glft(q, gamma, sigma, A, k):
    """delta_b = c1 + (q + 1/2) c2 ; delta_a = c1 - (q - 1/2) c2 (stationnaire : pas de T-t)."""
    c1, c2 = constantes_glft(gamma, sigma, A, k)
    return c1 + (q + 0.5) * c2, c1 - (q - 0.5) * c2


# ---------------------------------------------------------------- naïf
@njit(cache=True)
def profondeurs_naif(demi_spread):
    """Spread fixe, symétrique, aveugle à l'inventaire."""
    return demi_spread, demi_spread


# ---------------------------------------------------------------- placebo
@njit(cache=True)
def profondeurs_placebo(demi_moyen, tirage_bid, tirage_ask):
    """Profondeurs uniformes sur [0, 2m] (moyenne m), indépendantes du prix, de l'inventaire et du temps."""
    return 2.0 * demi_moyen * tirage_bid, 2.0 * demi_moyen * tirage_ask


# ---------------------------------------------------------------- aiguillage utilisé par le simulateur
@njit(cache=True)
def profondeurs_strategie(code, q, tau, gamma, sigma, k, A, demi_naif, cap, tirage_bid, tirage_ask):
    if code == CODE_PLACEBO:
        return profondeurs_placebo(demi_naif, tirage_bid, tirage_ask)
    if code == CODE_AS:
        return profondeurs_as(q, gamma, sigma, k, tau)
    if code == CODE_AS_PLAFONNE:
        return profondeurs_as_plafonne(q, gamma, sigma, k, tau, cap)
    if code == CODE_GLFT:
        return profondeurs_glft(q, gamma, sigma, A, k)
    return profondeurs_naif(demi_naif)


# ---------------------------------------------------------------- description d'une stratégie
@dataclass(frozen=True)
class Strategie:
    """Paramètres tels que le market maker CROIT le marché (sigma, A, k), pas tels qu'il est."""

    nom: str
    modele: str            # "naif" | "as" | "as_plafonne" | "glft" | "placebo"
    gamma: float           # aversion au risque (unités de chaque modèle : voir README)
    sigma: float           # pips / sqrt(s)
    k: float               # 1/pip
    A: float               # exécutions / s à profondeur nulle
    demi_naif: float       # pips (naïf : demi-spread fixe ; placebo : demi-spread moyen)
    cap: float             # pips (AS plafonné)
    Q: int                 # borne d'inventaire (lots)
    latence_pas: int = 1   # les cotes sont recalculées tous les `latence_pas` pas

    @property
    def code(self):
        return CODES[self.modele]


def gamma_pour_skew_cible(modele, skew_cible, q_ref, sigma, A, k, duree):
    """gamma tel qu'un inventaire q_ref décale la cote de `skew_cible` pips.

    gamma n'a pas la même unité dans AS (multiplié par T-t, jusqu'à 32 400 s) et GLFT
    (stationnaire) : les comparer à gamma égal n'aurait aucun sens. On égalise donc
    l'AGRESSIVITÉ de contrôle d'inventaire, pas gamma. Critère fixé a priori, pas optimisé.
    AS : décalage moyen sur la session (T-t = T/2). GLFT : pente c2.
    """
    if modele in ("as", "as_plafonne"):
        return skew_cible / (q_ref * sigma * sigma * duree / 2.0)
    return brentq(lambda g: q_ref * constantes_glft(g, sigma, A, k)[1] - skew_cible, 1e-9, 50.0)


def jeu_strategies_base(sigma, A, k, Q, duree, latence_pas=1):
    """Les 4 stratégies comparées, avec un critère d'agressivité commun.

    Critère : à Q/2 lots d'inventaire, la cote est décalée d'un demi-spread de base (1/k).
    Spread naïf = 2/k = limite risque-neutre d'AS (donc naïf = AS sans aucun contrôle d'inventaire).
    Plafond AS : le décalage ne dépasse pas 1/(2k), donc le côté à réduire garde au moins la
    moitié de son demi-spread de base au lieu de coter au mid.
    """
    cible, q_ref = 1.0 / k, Q / 2.0
    g_as = gamma_pour_skew_cible("as", cible, q_ref, sigma, A, k, duree)
    g_glft = gamma_pour_skew_cible("glft", cible, q_ref, sigma, A, k, duree)
    commun = dict(sigma=sigma, k=k, A=A, demi_naif=1.0 / k, cap=0.5 * cible, Q=Q, latence_pas=latence_pas)
    return [
        Strategie("Naïve symétrique", "naif", 0.0, **commun),
        Strategie("Avellaneda-Stoikov", "as", g_as, **commun),
        Strategie("AS skew plafonné", "as_plafonne", g_as, **commun),
        Strategie("GLFT asymptotique", "glft", g_glft, **commun),
    ]


def strategie_placebo(reference, demi_spread_moyen):
    """Cotes aléatoires de même largeur moyenne que `reference` : ce qui reste quand on retire toute logique."""
    return replace(reference, nom="Placebo (cotes aléatoires)", modele="placebo", gamma=0.0,
                   demi_naif=demi_spread_moyen)
