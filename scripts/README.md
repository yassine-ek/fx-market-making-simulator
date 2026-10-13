# `scripts/` : lancer les calculs et fabriquer les sorties

Les scripts « calcul » (`run_all.py`, `exporter_pnl_rejeu.py`, `construire_notebook.py`) lisent les données de marché (`HISTDATA_DIR`) ; les scripts « vitrine » ne lisent que `results/` et tournent sans données. Aucun script ne charge le TEST (`mm/donnees.py` l'interdit).

| Fichier | Ce qu'il fait / produit |
|---|---|
| `run_all.py` | Relance tout : calibration de σ (TRAIN), Monte Carlo, sensibilités, rejeu VAL des 30 variantes, placebo, contrôle marche aléatoire → `results/verdict_mm.json`, `results/rejeu_*` et les figures de `figures/`. `--rapide` : essai d'une minute dans des sous-dossiers `_rapide`. |
| `exporter_pnl_rejeu.py` | Recalcule seulement les 30 variantes du rejeu VAL (≈ 10 s, sans recalibrer σ) → `results/rejeu_pnl_quotidien.csv`, `rejeu_executions_quotidiennes.csv`, `rejeu_variantes.json` ; refuse d'écrire si un Sharpe s'écarte de `verdict_mm.json`. |
| `exporter_dashboard.py` | Écrit `docs/data.json`, `docs/data.js`, copie la page du gabarit commun et crée `docs/.nojekyll` (lit `results/`, sans données). |
| `generer_figures_vitrine.py` | Écrit `figures/hero_equity.png`, `toutes_variantes.png`, `overfit_scatter.png` (lit `results/`, sans données). |
| `generer_readme_tete.py` | Fonctions des blocs de chiffres du README (frais et hypothèses, métriques, « overfit ou pas ? », 30 variantes) ; seul, il réécrit ces blocs dans `README.md`. |
| `generer_readme.py` | Assemble le `README.md` entier depuis `modele_readme.md` et `results/` ; vérifie au passage que les affirmations qualitatives du texte tiennent (sinon il s'arrête). |
| `modele_readme.md` | Le modèle du README, avec des marqueurs `<<cle>>` remplacés par des chiffres lus dans les résultats. À éditer à la place du README. |
| `construire_notebook.py` | Génère `notebooks/visite_guidee.ipynb` (à exécuter ensuite avec nbconvert, voir le README principal). |
