# `tests/` : la suite pytest

Lancer : `python -m pytest -q` (quelques secondes). Les trois tests qui lisent les données HistData sont **sautés** (« skipped ») si `HISTDATA_DIR` n'est pas défini ; tous les autres sont synthétiques ou lisent `results/` et tournent n'importe où (c'est ce que fait l'intégration continue).
Principe : chaque brique est confrontée à une réponse connue (formule fermée, cas limite exact, barres écrites à la main), et les garanties de causalité et de non-ouverture du TEST sont des tests.

| Fichier | Ce qu'il fait |
|---|---|
| `test_modeles.py` | Formules d'Avellaneda-Stoikov et de GLFT (prix de réservation, spread, limite risque-neutre, antisymétrie, c1 et c2), stratégie naïve et placebo, critère d'agressivité commun. |
| `test_simulateur.py` | σ = 0 sans sélection adverse : capture de spread exacte ; exécutions conformes à la théorie de Poisson ; inventaire borné ; mêmes graines = mêmes résultats ; identité comptable PnL = cash + inventaire à 1e-9 ; latence ; sélection adverse. |
| `test_monte_carlo.py` | Sharpe de valeur connue, CVaR, IC bootstrap (se resserre avec n, plus large par blocs si autocorrélation), nombres aléatoires communs, placebo battu en simulation. |
| `test_calibration.py` | σ retrouvé à quelques pour cent sur barres synthétiques, trous de données sans fausse volatilité, moyenne en variance, TEST 2023+ scellé, grille de sensibilité grossière. |
| `test_rejeu.py` | Non-fuite des cotes, traversée de 0,1 pip, probabilité de file, ordre défavorable, inventaire borné, identité comptable, markout à la main, contrôle marche aléatoire, reproductibilité ; avec données : cotes sur prix réels et fuseau (réouverture hebdomadaire à 17h00 en juillet). |
| `test_significativite.py` | PSR et DSR contre des valeurs connues (Sharpe nul, signe, nombre d'essais croissant). |
| `test_variantes_rejeu.py` | Le PnL quotidien exporté redonne exactement les Sharpe, PnL moyens et exécutions de `results/verdict_mm.json` pour les 30 variantes ; drawdown ; assemblage sur barres synthétiques ; avec données : recalcul du cas de base AS. |
| `test_dashboard_et_readme.py` | `docs/data.json` cohérent avec `results/`, sans date ≥ 2023 ; `data.js` identique ; page identique au gabarit commun ; blocs de chiffres et README entier à jour ; un README par dossier ; aucun chemin absolu de machine. |
