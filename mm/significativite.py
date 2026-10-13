"""Significativité d'un Sharpe quand on a testé plusieurs variantes : PSR et DSR.

Mêmes formules que `04_alpha_research/alpha/stats.py` (Bailey et López de Prado, 2012 et 2014), sur des PnL
QUOTIDIENS ; les Sharpe de référence sont en unités PAR JOUR (non annualisés).

  PSR(SR*) = Φ( (SR - SR*)·√(n-1) / √(1 - γ3·SR + (γ4-1)/4·SR²) )   probabilité que le vrai Sharpe dépasse SR*
  SR0      = √V · ((1-γ)·Φ⁻¹(1-1/N) + γ·Φ⁻¹(1-1/(Ne)))             Sharpe maximal attendu de N essais SANS edge
  DSR      = PSR(SR0)                                                 PSR « déflaté » par le nombre d'essais
"""
import numpy as np
from scipy import stats as sps

EULER_MASCHERONI = 0.5772156649015329


def sharpe_quotidien(pnl):
    pnl = np.asarray(pnl, dtype=float)
    return float(pnl.mean() / pnl.std(ddof=1))


def psr(pnl, sr_ref=0.0):
    """Probabilistic Sharpe Ratio : P(vrai Sharpe quotidien > sr_ref), corrigé de l'asymétrie et de l'aplatissement."""
    x = np.asarray(pnl, dtype=float)
    sr = sharpe_quotidien(x)
    g3, g4 = sps.skew(x), sps.kurtosis(x, fisher=False)
    denom = np.sqrt(1.0 - g3 * sr + (g4 - 1.0) / 4.0 * sr ** 2)
    return float(sps.norm.cdf((sr - sr_ref) * np.sqrt(len(x) - 1) / denom))


def sharpe_reference_dsr(sharpes_essais):
    """SR0 : plus grand Sharpe quotidien attendu parmi N essais sans aucun vrai edge (variance observée des essais)."""
    s = np.asarray(sharpes_essais, dtype=float)
    n = len(s)
    if n < 2:
        return 0.0
    z1, z2 = sps.norm.ppf(1.0 - 1.0 / n), sps.norm.ppf(1.0 - 1.0 / (n * np.e))
    return float(np.sqrt(s.var(ddof=1)) * ((1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2))


def dsr(pnl, sharpes_essais):
    """Deflated Sharpe Ratio : PSR contre le Sharpe qu'on obtiendrait par pur hasard en testant ces essais."""
    return psr(pnl, sharpe_reference_dsr(sharpes_essais))
