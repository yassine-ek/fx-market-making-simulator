# `mm/` : le simulateur de market making

Le paquet Python du projet : formules de cotation, simulateur numba, Monte Carlo, rejeu sur barres réelles, les 30 variantes et leur significativité. Unités partout : prix en pips, temps en secondes, inventaire en lots (1 lot = 1 M EUR, donc 1 pip × 1 lot = 100 USD). Le TEST 2023+ est scellé : `donnees.py` refuse de le lire.

| Fichier | Rôle |
|---|---|
| `__init__.py` | Marque le dossier comme paquet. |
| `modeles.py` | Les cinq stratégies de cotation : naïve symétrique, Avellaneda-Stoikov (2008), AS à décalage plafonné, GLFT (2013), placebo (cotes aléatoires). Fonctions de profondeurs compilées numba, critère d'agressivité commun qui fixe γ sans l'optimiser, description d'une stratégie (`Strategie`). |
| `simulateur.py` | Noyau numba d'une session de 9 h (pas de 0,1 s) : mid brownien, exécutions de Poisson A·exp(-k·δ), sélection adverse (p, α), cotes périmées (latence), décomposition du PnL (capture, inventaire, liquidation, frais). Tous les aléas sont pré-tirés par `default_rng` : mêmes sessions pour toutes les stratégies. |
| `calibration.py` | Seule grandeur mesurée : σ par heure sur TRAIN 2010-2018 ; les hypothèses non mesurées (A, k, spread, p, α, frais, Q) et la grille 3×3 de sensibilité pour A et k. |
| `monte_carlo.py` | Sessions à tirages communs, Sharpe annualisé (√252), bootstrap simple et par blocs, CVaR, balayages à un et deux paramètres. |
| `rejeu_reel.py` | Rejeu sur barres 1 minute VAL 2019-2022 : cotes causales (close de la minute précédente), 3 modèles de fill, ordre intra-barre défavorable, deux lectures de « bid ET ask touchés », markout, placebo, marche aléatoire de contrôle. |
| `variantes_rejeu.py` | Les 30 variantes (5 stratégies × 3 modèles de fill × 2 conventions) : PnL quotidien net et exécutions par jour, statistiques (Sharpe et IC, drawdown, markout, PSR, DSR), écriture de `results/rejeu_*`. |
| `significativite.py` | PSR et DSR (Bailey et López de Prado) sur des PnL quotidiens. |
| `donnees.py` | Lecture des zips HistData EURUSD 1 minute (BID, heure de New York) depuis `HISTDATA_DIR` ; `PermissionError` pour 2023 et après. |
| `figures.py` | Toutes les figures PNG du Monte Carlo et du rejeu (une fonction par figure, aucun calcul). Les figures « vitrine » sont dans `scripts/generer_figures_vitrine.py`. |
