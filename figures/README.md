# `figures/` : les images du README

Toutes les images sont produites par un script (aucune n'est retouchée) ; aucune ne contient de données du TEST. PnL en pips × lot (1 pip × 1 lot = 100 USD) ou en millions de USD, nets de frais. Les trois premières sont les figures « vitrine » : elles ne lisent que `results/`.

| Image | Ce qu'elle montre | Script |
|---|---|---|
| `hero_equity.png` | Figure héro : PnL cumulé NET du rejeu VAL 2019-2022 pour les 5 stratégies (cas de base : probabiliste, côté perdant seul), drawdown en dessous, frais dans le titre, période de sélection 2019-2020 grisée. | `scripts/generer_figures_vitrine.py` |
| `toutes_variantes.png` | Les 30 variantes du rejeu en gris fin et le cas de base en couleur. | `scripts/generer_figures_vitrine.py` |
| `overfit_scatter.png` | Sharpe simulé (x) contre Sharpe du rejeu réel (y) pour chaque variante, diagonale, IC 95 % par blocs. | `scripts/generer_figures_vitrine.py` |
| `distributions_pnl.png` | Histogramme du PnL d'une session simulée de 9 h, une case par stratégie, moyenne et écart-type. | `scripts/run_all.py` (via `mm/figures.py`) |
| `decomposition_pnl.png` | PnL moyen par session décomposé : capture de spread, diffusion de l'inventaire, sélection adverse, liquidation, frais. | `scripts/run_all.py` |
| `trajectoire_exemple.png` | Deux minutes d'une session d'AS (mid, cotes, exécutions), inventaire, puis inventaire des cinq stratégies sur la session. | `scripts/run_all.py` |
| `sigma_par_heure.png` | Volatilité réalisée de l'EURUSD par heure de New York sur TRAIN 2010-2018 ; la session simulée en bleu. | `scripts/run_all.py` |
| `heatmap_p_k.png` | Sharpe simulé d'AS selon la sélection adverse p et le k réel du marché. | `scripts/run_all.py` |
| `heatmap_latence_gamma.png` | Sharpe simulé d'AS selon la latence et le gamma de la stratégie. | `scripts/run_all.py` |
| `heatmap_A_k.png` | Sharpe simulé des cinq stratégies selon les A et k réels (grille 3×3). | `scripts/run_all.py` |
| `sharpe_effondrement.png` | Sharpe simulé des cinq stratégies selon p, puis selon la latence (de 100 ms à 60 s). | `scripts/run_all.py` |
| `rejeu_modeles_fill.png` | Sharpe du rejeu par stratégie, modèle de fill et convention, avec IC 95 % par blocs de 10 jours. | `scripts/run_all.py` |
| `rejeu_sensibilite_f_seuil.png` | Sharpe du rejeu d'AS selon la probabilité de file f et la traversée exigée. | `scripts/run_all.py` |
| `rejeu_val_pnl_cumule.png` | PnL cumulé du rejeu (modèle de base) sous les deux lectures de « bid ET ask touchés ». | `scripts/run_all.py` |
| `markout_rejeu.png` | Markout moyen par exécution à +1, +5, +15 minutes : négatif et plat, comme sur une marche aléatoire. | `scripts/run_all.py` |
| `placebo_rejeu.png` | Sharpe et PnL moyen par jour d'AS et du placebo pour 30 graines de tirage. | `scripts/run_all.py` |
