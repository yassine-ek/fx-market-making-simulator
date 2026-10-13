# `docs/` : le tableau de bord interactif (GitHub Pages)

Page statique qui permet de choisir les conditions de départ (nombre d'exécutions minimum et Sharpe minimum sur la période de sélection, stratégie, modèle de fill, convention pour « bid ET ask touchés »), de combiner les variantes retenues (moyenne équipondérée) et de lire la courbe finale avec ses métriques et un voyant « Overfit ? ». Pas de serveur nécessaire : ouvrir `index.html` (les données sont dans `data.js`) ou publier le dossier avec GitHub Pages.

**Ce que contiennent les 30 variantes.** Chaque variante est un rejeu de VAL 2019-2022 sur EURUSD 1 minute : 5 stratégies × 3 modèles de fill × 2 conventions. Le rendement quotidien est le PnL net de frais (frais d'exécution et coût de liquidation déjà déduits) en USD, divisé par un capital de référence arbitraire de 100 M USD : ce choix change l'échelle des courbes et des drawdowns en %, jamais le Sharpe.

**Honnêteté sur la sélection.** Le rejeu ne couvre que VAL : il n'existe pas de TRAIN rejoué (TRAIN ≤ 2018 ne sert qu'à calibrer σ). Pour que le filtre ait un sens, VAL est coupée en deux moitiés : **sélection 2019-2020** et **évaluation 2021-2022** (frontières `train_fin = 2020-12-31` et `val_fin = 2022-12-31` dans `data.json`). Le gabarit commun affiche ces deux noms (« SÉLECTION 2019-2020 » et « ÉVALUATION 2021-2022 ») grâce à son champ facultatif `libelles`, écrit dans `data.json`. Les filtres (nombre d'exécutions, Sharpe) n'utilisent que la période de sélection ; la courbe est affichée sur les deux périodes. Cette coupure est un exercice de présentation, pas un second hors-échantillon indépendant (l'auteur a vu toute la période VAL) ; toutes les variantes ont un Sharpe négatif, donc aucun filtre ne crée d'edge. Aucune donnée ≥ 2023 : le TEST est scellé.

| Fichier | Rôle |
|---|---|
| `index.html` | La page (copie du gabarit commun `projets_cv/_outils/dashboard/`) ; charge Plotly 2.35.0 depuis cdnjs. |
| `data.json` | Rendements quotidiens nets des 30 variantes, leurs statistiques de sélection (exécutions, Sharpe, PnL par jour), filtres, frais. Généré. |
| `data.js` | Même contenu que `data.json`, sous la forme `window.DATA = ...`, pour l'ouverture directe en `file://`. Généré. |
| `.nojekyll` | Fichier vide : demande à GitHub Pages de servir les fichiers tels quels. |

Régénérer `data.json`, `data.js` et la page : `python scripts/exporter_dashboard.py` (lit `results/`, aucune donnée de marché requise).
