# `results/` : les sorties figées

Tous les chiffres du README sont lus ici (aucun n'est tapé à la main). Les fichiers sont produits par les scripts, ne sont pas à éditer, et ne contiennent aucune donnée du TEST (le dernier jour rejoué est le 2022-12-30). PnL en pips × lot (1 pip × 1 lot = 100 USD), nets de frais d'exécution et de liquidation.

| Fichier | Contenu | Produit par |
|---|---|---|
| `verdict_mm.json` | Le verdict complet : hypothèses, calibration de σ, Monte Carlo (Sharpe, IC, CVaR, décomposition du PnL), sensibilités (p, latence, γ, A, k), rejeu VAL (3 modèles de fill × 2 conventions × 5 stratégies, markout, placebo, sensibilité à f et au seuil, contrôle marche aléatoire). | `scripts/run_all.py` |
| `rejeu_variantes.json` | Les 30 variantes du rejeu : libellé, Sharpe et IC 95 % par blocs, PnL moyen, drawdown, jours gagnants, exécutions, frais, markout, PSR, DSR ; méta (graine, capital de référence, périodes du tableau de bord). | `scripts/exporter_pnl_rejeu.py` ou `scripts/run_all.py` |
| `rejeu_pnl_quotidien.csv` | PnL net de chaque variante pour chacune des 1 036 journées 2019-01-02 → 2022-12-30 (une colonne par identifiant de variante) ; source du tableau de bord, de la figure héro et des tableaux du README. | idem |
| `rejeu_executions_quotidiennes.csv` | Nombre d'exécutions par jour et par variante. | idem |

Un essai `run_all.py --rapide` écrit dans `results/_rapide/` (ignoré par git) et n'écrase jamais ces fichiers.
