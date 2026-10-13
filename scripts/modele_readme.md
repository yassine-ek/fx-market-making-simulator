<!-- Fichier généré par scripts/generer_readme.py à partir de scripts/modele_readme.md : éditer le modèle, pas ce fichier. -->
# Market making FX : le Sharpe simulé est une borne haute, pas un Sharpe de marché

Simulateur de market making EURUSD (Avellaneda-Stoikov, GLFT, naïf, placebo) à noyau numba et Monte Carlo à tirages communs, comparé à un rejeu sur quatre ans de barres 1 minute réelles pour montrer d'où vient le PnL d'un market maker et quelle part n'est qu'un artefact du simulateur.

- **At a glance.** FX market-making simulator (Avellaneda-Stoikov, GLFT, naive quotes, random-quote placebo): numba core, Monte Carlo with common random numbers, replay on four years of real EURUSD 1-minute bars (30 variants, test set sealed).
- **Result.** Simulated annualised Sharpe from <<sh_min_en>> to <<sh_max_en>>, valid only inside the model's own world; the replay is negative for all 30 variants (<<rj_var_min_en>> to <<rj_var_max_en>>) and a driftless random-walk control gives losses of the same order, so the replay measures the fill convention, not the market.
- **Limits.** A, k, p and α are assumptions (no order data); 1-minute bars imply about 60 s of quote latency; no L2 book; the "loser side" fill rule uses the bar's close, a pessimistic choice made after the fact.

[![tests](https://github.com/yassine-ek/fx-market-making-simulator/actions/workflows/tests.yml/badge.svg)](https://github.com/yassine-ek/fx-market-making-simulator/actions/workflows/tests.yml) ![python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue) ![licence](https://img.shields.io/badge/licence-MIT-lightgrey)

## Résultats clés

<!-- AUTO:CLES -->
<<bloc_cles>>
<!-- /AUTO:CLES -->

![PnL cumulé net de frais du rejeu VAL pour les 5 stratégies, cas de base, avec drawdown en dessous](figures/hero_equity.png)

*Rejeu sur EURUSD 1 minute réel (2019-2022), net de frais, cinq stratégies, cas de base ; drawdown en dessous. Échelle : 1 M USD = 1 % d'un capital de référence arbitraire de <<capital_ref>> M USD. Les cinq courbes se superposent et descendent régulièrement : la perte ne vient pas d'une période mais de la convention de fill (contrôle marche aléatoire plus bas).*

**Liens** : [tableau de bord interactif](https://yassine-ek.github.io/fx-market-making-simulator/) · [notebook guidé](notebooks/visite_guidee.ipynb) · [détails : méthode, résultats, tests](docs/details.md) · [reproduire](#reproduire)

<!-- AUTO:TETE -->
<<bloc_tete>>
<!-- /AUTO:TETE -->

<!-- AUTO:OVERFIT -->
<<bloc_overfit>>
<!-- /AUTO:OVERFIT -->

## Toutes les variantes

Rien n'est caché : les **30 variantes du rejeu** (5 stratégies × 3 modèles de fill × 2 conventions pour le cas « bid ET ask touchés ») sont publiées, **y compris les moins mauvaises et les pires**, ainsi que les balayages Monte Carlo (sélection adverse, latence, γ, A, k). Aucune variante n'est choisie sur son résultat : la grille est fixée avant le premier rejeu. Le même PnL quotidien de chaque variante alimente le tableau de bord interactif (identifiants identiques).

![Toutes les variantes : PnL cumulé net des 30 rejeux, cas de base en couleur](figures/toutes_variantes.png)

**Comment lire ce graphique.** Chaque ligne grise est le PnL cumulé net d'une des 25 variantes autres que le cas de base ; les cinq lignes en couleur (quasi superposées) sont le cas de base. L'éventail des PnL cumulés finaux va de <<cumul_haut>> à <<cumul_bas>> millions de USD (de <<cumul_haut_pct>> % à <<cumul_bas_pct>> % du capital de référence arbitraire de <<capital_ref>> M USD) : la convention de fill déplace l'ampleur de la perte (le groupe le plus bas est « côté perdant seul » avec f = 1, où chaque barre qui traverse la cote est exécutée et, par construction, du côté qui perd), jamais son signe. Aucune courbe ne monte.

![Sharpe du rejeu réel contre Sharpe simulé pour les 30 variantes](figures/overfit_scatter.png)

**Comment lire ce graphique.** Un point par variante : Sharpe annualisé de la **simulation** en abscisse (le même pour les 6 variantes d'une stratégie), Sharpe du **rejeu sur marché réel** en ordonnée, avec son IC 95 % par blocs de 10 jours. Sur la diagonale, le réel ferait aussi bien que la simulation. Ici tous les points sont très en dessous, sous zéro : plein = côté perdant seul, creux = les deux côtés ; la forme est le modèle de fill. Le « hors échantillon » de ce projet est le marché réel : c'est là que le Sharpe simulé s'effondre.

<!-- AUTO:VARIANTES -->
<<bloc_variantes>>
<!-- /AUTO:VARIANTES -->

## Tableau de bord interactif

Choisissez vous-même les conditions de départ : **nombre d'exécutions minimum** et **Sharpe minimum** sur la période de sélection (2019-2020), stratégies, modèles de fill, convention. Seules les variantes qui passent ces filtres sont combinées (moyenne équipondérée) ; la courbe est affichée sur 2019-2020 puis sur 2021-2022 (évaluation), avec ses métriques recalculées et un voyant « Overfit ? ».

- En ligne : <https://yassine-ek.github.io/fx-market-making-simulator/>
- Ou ouvrir `docs/index.html` localement (les données sont dans `docs/data.js`, aucun serveur nécessaire ; sinon lancer `python -m http.server` dans `docs/`).
- Régénérer : `python scripts/exporter_dashboard.py` (lit `results/`, aucune donnée de marché requise).

Le rejeu ne couvre que VAL 2019-2022 : la coupure « sélection 2019-2020 / évaluation 2021-2022 » est un choix de présentation (frontières `train_fin = 2020-12-31`, `val_fin = 2022-12-31` dans `docs/data.json`), pas un second jeu de test, car les 30 variantes sont fixées avant et toutes ont un Sharpe négatif : aucun filtre ne peut créer d'edge, il montre ce que coûte la convention de fill. Les rendements sont le PnL net en USD divisé par un capital de référence arbitraire de <<capital_ref>> M USD (ne change pas le Sharpe). TEST 2023+ n'apparaît jamais.

## Pourquoi ce projet

Métiers visés : market making, exécution, plateformes de trading FX. Le dépôt montre comment lire un backtest de market making sans se tromper de conclusion : un simulateur dont le monde obéit au modèle, un rejeu sur données réelles, des contrôles (placebo, marche aléatoire) et des tests qui verrouillent la comptabilité, l'absence de fuite et le scellé du TEST.

## Méthode en bref

- **Stratégies** (`mm/modeles.py`) : naïve symétrique (spread fixe), Avellaneda-Stoikov 2008 (décale ses cotes contre l'inventaire), AS à décalage plafonné, GLFT 2013 (version asymptotique) et un placebo aux cotes aléatoires de même largeur moyenne. Même borne d'inventaire Q = 20 lots pour toutes.
- **Simulateur** (`mm/simulateur.py`) : pas de 0,1 s sur 9 h, mid brownien de volatilité σ, exécutions de Poisson d'intensité A·exp(-k·δ), sélection adverse (probabilité p, saut α), cotes périmées entre deux mises à jour (latence). Tous les nombres aléatoires sont pré-tirés : toutes les stratégies voient les mêmes sessions.
- **Rejeu** (`mm/rejeu_reel.py`) : cotes causales autour du close de la minute précédente, fill seulement si la barre suivante traverse la cote, 3 modèles de fill × 2 lectures de « bid ET ask touchés ».
- **γ** : même grandeur (aversion au risque) dans AS et GLFT, mais pas le même effet à γ égal ; on égalise donc l'agressivité (décalage de 1/k pip à Q/2 lots) plutôt que γ, critère fixé a priori ([détail](docs/details.md#méthode)).

## Limites (dites franchement)

- **A, k, p, α, spread et frais sont des hypothèses**, pas des mesures (aucune donnée d'ordres). Le Monte Carlo est conditionnel à elles.
- Le monde simulé **obéit au modèle** testé (mouvement brownien, intensités exponentielles) : la supériorité d'AS/GLFT sur le naïf y est presque tautologique.
- **Convention « côté perdant seul » (cas de base du rejeu).** Quand une même barre touche le bid et l'ask, le côté exécuté est celui dont le **close de la barre** s'éloigne : une information postérieure à la pose de la cote, retournée contre la stratégie. C'est un **choix pessimiste fait a posteriori, pas une hypothèse de remplissage réaliste** ; le cas de base n'estime donc pas le PnL d'un vrai market maker (« les deux côtés » est la lecture optimiste).
- Fills de Poisson **indépendants du prix** hors sélection adverse : vraisemblablement une borne haute ; le rejeu sur barres, où chaque fill est conditionné au mouvement du prix, est vraisemblablement une borne basse (ni l'une ni l'autre n'est démontrée). La vérité est probablement entre les deux, et on ne sait pas où.
- Rejeu sur barres 1 minute : pas de carnet L2, pas de position dans la file (seulement un facteur f), 1 lot par exécution, pas d'impact, **60 s de latence implicite**, un demi-spread de marché constant ajouté à des prix BID, ordre intra-barre inconnu.
- **Deux σ de minute** : <<sigma_minute>> pips (calibration TRAIN 2010-2018, utilisée par le Monte Carlo) contre <<ctl_sigma>> pips mesurés sur les barres VAL (utilisés par le rejeu et son contrôle) : VAL est moins volatil que TRAIN. Le σ du simulateur n'est pas recalibré sur VAL (ce serait ajuster la simulation sur la période d'évaluation) ; explication dans les [détails](docs/details.md#données-et-hypothèses).
- σ constant dans la session (pas de saisonnalité intra-session ni de sauts hors sélection adverse) ; session 03h-12h heure de New York = 08h-17h Londres toute l'année sauf ~3 semaines par an où les heures d'été US et européenne diffèrent (décalage d'1 h non corrigé).
- Un seul actif (EURUSD), pas de hedge actif de l'inventaire ni de multi-fournisseurs de liquidité.
- VAL seul est lu, le TEST reste scellé : aucun verdict out-of-sample final n'est prétendu. Le DSR est calculé sur les 30 variantes du rejeu (tous les Sharpe sont négatifs, donc le DSR est nul) ; il ne couvre ni les balayages Monte Carlo ni les choix de conception, et les IC du rejeu ne corrigent pas le nombre d'essais.
- Les PnL en M USD sont rapportés à un capital de référence **arbitraire** de <<capital_ref>> M USD : ils ne représentent aucun PnL réel.
- Le tableau de bord coupe VAL en deux moitiés : exercice de présentation, pas un second hors-échantillon indépendant (l'auteur a vu toute la période VAL). Les IC bootstrap supposent des sessions indépendantes en simulation (vrai par construction) et des blocs de 10 jours dans le rejeu (choix a priori, non optimisé).

## Pour aller plus loin

[`docs/details.md`](docs/details.md) contient : le tableau complet des frais et hypothèses, la méthode (formules, simulateur, données, σ), les résultats détaillés du Monte Carlo et du rejeu (modèles de fill, markout, placebo, contrôle marche aléatoire), la sensibilité à la sélection adverse et à la latence, la validation par les tests, le positionnement face aux dépôts GitHub existants et un résumé en anglais. Chaque dossier du dépôt a son propre `README.md`.

<details>
<summary>Structure du dépôt</summary>

```
.
├── README.md                    ce fichier : résultats clés, frais, métriques simulation | rejeu, lecture « overfit ou pas ? »
├── LICENSE  requirements.txt  pytest.ini  conftest.py  .gitignore  .gitattributes  .github/workflows/tests.yml
├── mm/                          le paquet : formules, simulateur numba, Monte Carlo, rejeu, 30 variantes, PSR/DSR, figures
├── scripts/                     calcul complet, export du PnL quotidien et du tableau de bord, figures vitrine, génération des README et du carnet
├── tests/                       suite pytest (synthétique, sauf les tests qui lisent les données locales)
├── notebooks/                   visite guidée : intuition → formule → attente → code → lecture
├── results/                     sorties figées (JSON, CSV du PnL quotidien) dont sont tirés tous les chiffres
├── figures/                     images du README (héro, toutes variantes, scatter, Monte Carlo, rejeu)
└── docs/                        tableau de bord interactif (GitHub Pages : index.html, data.json, data.js) et details.md
```

</details>

## Comment ce projet a été construit

Projet réalisé en octobre 2026 avec un assistant de programmation IA (Claude, Anthropic) que j'ai dirigé : choix des sujets, protocole, vérification des résultats. Tous les chiffres sont régénérés par les scripts du dépôt et contrôlés par les tests et la CI.

## Reproduire

```bash
pip install -r requirements.txt

# 1. Sans données de marché : tests, puis tout ce qui se régénère depuis results/
python -m pytest -q                        # les tests qui lisent les données sont sautés (« skipped »)
python scripts/exporter_dashboard.py       # -> docs/data.json, docs/data.js
python scripts/generer_figures_vitrine.py  # -> figures/hero_equity.png, toutes_variantes.png, overfit_scatter.png
python scripts/generer_readme.py           # -> README.md et docs/details.md, chiffres lus dans results/

# 2. Avec les données HistData (voir « Obtenir les données ») : définir HISTDATA_DIR
export HISTDATA_DIR=/chemin/vers/donnees   # PowerShell : $env:HISTDATA_DIR = "D:/donnees"
python -m pytest -q                        # suite complète
python scripts/run_all.py                  # tout recalculer (quelques minutes) ; --rapide : 1 minute, écrit dans des sous-dossiers _rapide
python scripts/exporter_pnl_rejeu.py       # seulement le PnL quotidien des 30 variantes (~10 s) -> results/rejeu_*.csv et rejeu_variantes.json
python scripts/construire_notebook.py && python -m jupyter nbconvert --to notebook --execute --inplace notebooks/visite_guidee.ipynb
```

Graines : 20260713 (Monte Carlo), 777 (sensibilités), 20260714 (rejeu) ; les sessions sont indexées, donc 2 000 sessions = les mêmes 2 000 sessions à chaque relance. Dépendances : Python 3.12+, numpy, numba, scipy, pandas, matplotlib, pytest ; nbformat, nbconvert et ipykernel seulement pour fabriquer et exécuter le carnet.

### Obtenir les données

Les barres EURUSD 1 minute viennent de [HistData](https://www.histdata.com) (téléchargement gratuit, manuel, une archive par année de 2010 à 2022 ; elles ne sont pas redistribuées ici et le TEST 2023+ n'est jamais lu). Arborescence attendue, sous le dossier désigné par la variable d'environnement `HISTDATA_DIR` (défaut : `./data/histdata`, ignoré par git) :

```
$HISTDATA_DIR/histdata_raw/EURUSD/EURUSD_2010.zip
$HISTDATA_DIR/histdata_raw/EURUSD/EURUSD_2011.zip
...
$HISTDATA_DIR/histdata_raw/EURUSD/EURUSD_2022.zip      # un .csv de minutes (BID) par archive
```

Sans ces fichiers, `pytest` saute les tests qui lisent les données et les scripts de calcul s'arrêtent avec un message qui rappelle cette arborescence ; les scripts « vitrine » (figures, tableau de bord, README) n'en ont pas besoin, car tout est relu dans `results/`.
