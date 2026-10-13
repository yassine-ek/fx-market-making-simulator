# Projet 02 : un market maker FX qui gagne en simulation et perd en rejeu, et pourquoi

Simulateur de market making FX (Avellaneda-Stoikov, GLFT, naïf, placebo) avec noyau numba, Monte Carlo à tirages communs et rejeu sur barres EURUSD 1 minute réelles. L'objectif n'est pas de « battre le marché » : c'est de **montrer d'où vient le PnL d'un market maker, et combien de ce PnL est un artefact du simulateur**.

*An FX market-making simulator (Avellaneda-Stoikov, GLFT, naive quotes, random-quote placebo) with a Monte Carlo engine and a replay on real EURUSD 1-minute bars: the simulated Sharpe is an upper bound, and a random-walk control shows that the replay measures the fill convention, not the market.*

![tests](https://img.shields.io/badge/tests-63%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue) ![licence](https://img.shields.io/badge/licence-MIT-lightgrey)

<!-- AUTO:TETE -->
### Frais et hypothèses

| Hypothèse | Valeur |
|---|---|
| Frais par exécution | **0,005 pip par exécution** (≈ 0,5 USD par million : ordre de grandeur, non vérifié) + coût de liquidation de l'inventaire résiduel en fin de session (demi-spread de marché 0,10 pip × lots détenus). Tous les PnL des tableaux et des figures sont **NETS** de ces deux coûts ; 1 pip × 1 lot (1 M EUR) = 100 USD |
| Spread de marché | demi-spread 0,10 pip (hypothèse ; EURUSD interbancaire ≈ 0,1-0,3 pip de spread), ajouté aux prix BID de HistData pour reconstituer le mid |
| Hypothèses A, k, p, α | A = 0,10 exécution/s à profondeur 0 par côté · k = 6,0 /pip · p = 0,20 (proba de saut après exécution) · α = 0,30 pip (taille du saut). **Hypothèses, pas des mesures** (aucune donnée d'ordres), fixées avant les résultats, sensibilités publiées ; elles pilotent la simulation, pas le rejeu |
| Latence | simulation : cotes recalculées toutes les 0,1 s (balayage jusqu'à 60 s) ; rejeu sur barres 1 minute : la cote de la minute *i* repose sur le close de *i*-1, soit **60 s de latence implicite** |
| Données | EURUSD 1 minute **HistData, prix BID, heure locale de New York** (heure d'été comprise), volume nul ; session 03h00-12h00 (= 08h-17h Londres) ; 1 036 journées de rejeu (2019-01-02 → 2022-12-30) ; données non redistribuées (voir « Reproduire ») |
| Découpage | **TRAIN ≤ 2018** : calibration de σ seulement (σ = 0,330 pip/√s), rien n'y est rejoué · **VAL 2019-2022** : rejeu · **TEST 2023+ : scellé**, jamais lu (`mm/donnees.py` lève `PermissionError`, testé) |
| Conventions de fill | 3 modèles : *touche* (traversée ≥ 0,0 pip, f = 1,0), *traversée* (≥ 0,1 pip, f = 1,0), *probabiliste* (≥ 0,1 pip, file d'attente f = 0,5) × 2 lectures du cas « bid ET ask touchés » (côté perdant seul / les deux côtés). Cas de base : probabiliste + côté perdant seul |
| Délai d'exécution | fill testé sur la barre qui SUIT la pose de la cote, jamais au prix du signal ; ordre intra-barre inconnu, on suppose l'ordre défavorable |
| Statistiques | Sharpe journalier × √252 ; IC 95 % par bootstrap par blocs de 10 jours (rejeu) ou des sessions (simulation, 2 000 sessions) ; PSR et DSR sur les 30 variantes du rejeu |

### Métriques par stratégie : simulation et rejeu réel côte à côte

Équivalent ici du « TRAIN | VAL » d'un projet de stratégie : à gauche le monde **simulé** (les hypothèses du modèle sont vraies par construction), à droite le **rejeu sur EURUSD réel** VAL 2019-2022 (cas de base : probabiliste, côté perdant seul). PnL en pips × lot par journée.

| Stratégie | Sharpe simulé [IC95] | Sharpe rejeu VAL net [IC95, blocs de 10 j] | Rapport rejeu / simulé | PnL moyen/jour simulé | PnL moyen/jour rejeu | Exécutions/jour simulé | Exécutions/jour rejeu |
|---|---|---|---|---|---|---|---|
| Naïve symétrique | 7,0 [6,3 ; 7,8] | -10,9 [-12,0 ; -10,0] | -1,56 | 298 | -287 | 2 325 | 267 |
| Avellaneda-Stoikov | 25,0 [23,9 ; 26,0] | -14,6 [-16,1 ; -13,2] | -0,58 | 302 | -287 | 2 319 | 267 |
| AS skew plafonné | 24,7 [23,7 ; 25,8] | -12,9 [-14,2 ; -11,8] | -0,52 | 303 | -288 | 2 315 | 268 |
| GLFT asymptotique | 36,0 [34,8 ; 37,3] | -15,0 [-16,5 ; -13,7] | -0,42 | 306 | -288 | 2 320 | 267 |
| Placebo (cotes aléatoires) | 5,7 [5,0 ; 6,4] | -10,6 [-11,7 ; -9,5] | -1,86 | 246 | -279 | 2 637 | 266 |

### Rejeu VAL, cas de base : pertes, drawdown, frais payés et significativité

| Stratégie | PnL cumulé 2019-2022 (M USD) | Drawdown max (M USD) | Jours gagnants | Frais + liquidation payés / jour (pips × lot) | Markout +1 min, côté perdant (pip) | Markout +1 min, deux côtés (pip) | PSR(0) | DSR (30 essais) |
|---|---|---|---|---|---|---|---|---|
| Naïve symétrique | -29,8 | -29,8 | 17,8 % | 2,3 | -1,10 | -0,27 | < 0,001 | < 0,001 |
| Avellaneda-Stoikov | -29,8 | -29,8 | 6,7 % | 2,1 | -1,10 | -0,28 | < 0,001 | < 0,001 |
| AS skew plafonné | -29,8 | -29,9 | 9,5 % | 2,1 | -1,09 | -0,27 | < 0,001 | < 0,001 |
| GLFT asymptotique | -29,9 | -29,9 | 6,5 % | 1,9 | -1,10 | -0,28 | < 0,001 | < 0,001 |
| Placebo (cotes aléatoires) | -28,9 | -28,9 | 18,1 % | 2,3 | -1,09 | -0,29 | < 0,001 | < 0,001 |

*Drawdown = pire baisse du PnL cumulé depuis son sommet (le PnL décroît presque en continu : drawdown ≈ perte totale). Markout = (mid futur − prix d'exécution) × sens, par exécution. Les frais et la liquidation (quelques pips × lot par jour) ne sont pas la cause de la perte : la convention de fill l'est (contrôle marche aléatoire plus bas).*

**Verdict.** Aucune des 30 variantes du rejeu n'a un Sharpe positif (de -23,2 à -3,4) alors que la simulation donnait +5,7 à +36,0. Mais le même rejeu sur 400 journées de marche aléatoire sans dérive donne un PnL du même ordre : le rejeu mesure le coût de la convention de fill sur barres de 1 minute, pas une propriété du marché réel. Le Sharpe simulé est une **borne haute**, pas un Sharpe de marché. TEST scellé.
<!-- /AUTO:TETE -->

![PnL cumulé net de frais du rejeu VAL pour les 5 stratégies, cas de base, avec drawdown en dessous](figures/hero_equity.png)

**Comment lire ce graphique.** PnL cumulé en millions de USD du rejeu sur EURUSD 1 minute réel (2019-2022), **net de frais** (rappelés dans le titre), pour les cinq stratégies dans le cas de base. Le panneau du bas est le drawdown (distance au dernier sommet du PnL cumulé).
Les cinq courbes sont quasi superposées et descendent régulièrement : la perte ne vient pas d'une période particulière mais de la convention de fill (voir le contrôle marche aléatoire plus bas). La zone grisée 2019-2020 est la période de sélection du tableau de bord interactif, la zone blanche 2021-2022 sa période d'évaluation : il n'existe pas de TRAIN rejoué ici, TRAIN ≤ 2018 ne sert qu'à calibrer σ.

<!-- AUTO:OVERFIT -->
### Overfit ou pas ? Lecture en 30 secondes

1. **Simulation contre marché réel : le Sharpe change de signe.** Sharpe simulé → Sharpe du rejeu (cas de base) : Naïve symétrique 7,0 → -10,9, Avellaneda-Stoikov 25,0 → -14,6, AS skew plafonné 24,7 → -12,9, GLFT asymptotique 36,0 → -15,0, Placebo (cotes aléatoires) 5,7 → -10,6. Le rapport rejeu / simulé va de -1,86 à -0,42, et les 30 variantes du rejeu sont toutes négatives. Ce n'est pas un overfit au sens classique (rien n'a été ajusté sur la simulation : tous les paramètres sont fixés a priori) mais un écart de monde : le Sharpe simulé est une borne haute.
2. **Le placebo (cotes aléatoires) fait aussi bien qu'Avellaneda-Stoikov.** Dans le rejeu, PnL moyen par jour de -288 (AS) contre -279 (placebo), côté perdant seul ; AS fait mieux dans 13 % des 30 graines seulement. La logique d'inventaire n'apporte aucun gain d'espérance sur ces barres.
3. **Contrôle marche aléatoire : le rejeu ne distingue pas l'EURUSD réel d'une marche sans dérive (même ordre de grandeur).** PnL moyen par jour de la stratégie naïve, côté perdant seul : -287 sur barres réelles contre -359 sur marche aléatoire (markout +1 min : -1,10 contre -1,33 pip). Le Sharpe négatif du rejeu mesure la convention de fill, pas le marché.
4. **DSR : < 0,001 pour 30 essais** (les 30 variantes publiées ; PSR(0) maximal < 0,001) : il n'y a aucun Sharpe positif à déflater. La borne haute de l'IC 95 % du Sharpe du rejeu la plus favorable est -2,4 : zéro est exclu pour les 30 variantes.
5. **Choisi AVANT de voir VAL : tout.** A, k, p, α, spread, frais, Q, le critère d'agressivité commun de γ (décalage de 1/k à Q/2 lots), les 3 modèles de fill, les 2 conventions et les 5 stratégies sont fixés avant le premier rejeu ; la seule grandeur calibrée est σ, sur TRAIN ≤ 2018. Aucune variante n'est retirée après coup : les 30 sont publiées. Les deux ajouts postérieurs (correction de la description du fuseau, contrôle marche aléatoire) viennent de la relecture adversariale du 13/10 et ne changent aucun chiffre existant.
<!-- /AUTO:OVERFIT -->

## Toutes les variantes

Rien n'est caché : les **30 variantes du rejeu** (5 stratégies × 3 modèles de fill × 2 conventions pour le cas « bid ET ask touchés ») sont ici, **y compris les moins mauvaises et les pires**, ainsi que les balayages Monte Carlo (sélection adverse, latence, γ, A, k). Aucune variante n'est choisie sur son résultat : la grille est fixée avant le premier rejeu.
Le même PnL quotidien de chaque variante alimente le tableau de bord interactif (identifiants identiques).

<!-- AUTO:VARIANTES -->
| Variante | Modèle de fill | Si bid ET ask touchés | Stratégie | Sharpe rejeu [IC95, blocs de 10 j] | PnL moyen/jour (pips × lot) | PnL cumulé (M USD) | Exécutions/jour | Markout +1 min (pip) | PSR(0) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|
| `NAI-T-perd` | touche | côté perdant seul | Naïve | -17,8 [-19,6 ; -16,3] | -578 | -59,8 | 537 | -1,08 | < 0,001 | < 0,001 |
| `AS-T-perd` | touche | côté perdant seul | Avellaneda-Stoikov | -22,8 [-26,2 ; -20,3] | -576 | -59,7 | 538 | -1,09 | < 0,001 | < 0,001 |
| `ASP-T-perd` | touche | côté perdant seul | AS skew plafonné | -20,4 [-23,2 ; -18,4] | -572 | -59,2 | 538 | -1,08 | < 0,001 | < 0,001 |
| `GLFT-T-perd` | touche | côté perdant seul | GLFT | -23,2 [-26,7 ; -20,6] | -574 | -59,5 | 538 | -1,09 | < 0,001 | < 0,001 |
| `PLA-T-perd` | touche | côté perdant seul | Placebo | -17,4 [-18,9 ; -16,1] | -560 | -58,0 | 536 | -1,08 | < 0,001 | < 0,001 |
| `NAI-T-deux` | touche | les deux côtés | Naïve | -5,5 [-6,5 ; -4,5] | -133 | -13,8 | 871 | -0,16 | < 0,001 | < 0,001 |
| `AS-T-deux` | touche | les deux côtés | Avellaneda-Stoikov | -13,5 [-15,1 ; -12,2] | -156 | -16,1 | 861 | -0,17 | < 0,001 | < 0,001 |
| `ASP-T-deux` | touche | les deux côtés | AS skew plafonné | -13,3 [-14,8 ; -12,0] | -154 | -16,0 | 862 | -0,17 | < 0,001 | < 0,001 |
| `GLFT-T-deux` | touche | les deux côtés | GLFT | -16,2 [-18,2 ; -14,3] | -152 | -15,8 | 861 | -0,17 | < 0,001 | < 0,001 |
| `PLA-T-deux` | touche | les deux côtés | Placebo | -5,9 [-7,0 ; -4,9] | -143 | -14,9 | 857 | -0,18 | < 0,001 | < 0,001 |
| `NAI-X-perd` | traversée | côté perdant seul | Naïve | -17,6 [-19,4 ; -16,1] | -568 | -58,9 | 533 | -1,08 | < 0,001 | < 0,001 |
| `AS-X-perd` | traversée | côté perdant seul | Avellaneda-Stoikov | -22,4 [-25,8 ; -20,0] | -574 | -59,4 | 534 | -1,09 | < 0,001 | < 0,001 |
| `ASP-X-perd` | traversée | côté perdant seul | AS skew plafonné | -20,4 [-23,1 ; -18,4] | -573 | -59,3 | 534 | -1,09 | < 0,001 | < 0,001 |
| `GLFT-X-perd` | traversée | côté perdant seul | GLFT | -22,9 [-26,3 ; -20,5] | -574 | -59,5 | 534 | -1,09 | < 0,001 | < 0,001 |
| `PLA-X-perd` | traversée | côté perdant seul | Placebo | -17,5 [-19,2 ; -16,2] | -558 | -57,9 | 531 | -1,08 | < 0,001 | < 0,001 |
| `NAI-X-deux` | traversée | les deux côtés | Naïve | -7,9 [-8,9 ; -7,0] | -202 | -20,9 | 805 | -0,27 | < 0,001 | < 0,001 |
| `AS-X-deux` | traversée | les deux côtés | Avellaneda-Stoikov | -17,5 [-19,4 ; -15,8] | -226 | -23,4 | 797 | -0,28 | < 0,001 | < 0,001 |
| `ASP-X-deux` | traversée | les deux côtés | AS skew plafonné | -17,0 [-18,8 ; -15,3] | -223 | -23,1 | 799 | -0,28 | < 0,001 | < 0,001 |
| `GLFT-X-deux` | traversée | les deux côtés | GLFT | -20,9 [-23,1 ; -18,6] | -224 | -23,2 | 797 | -0,28 | < 0,001 | < 0,001 |
| `PLA-X-deux` | traversée | les deux côtés | Placebo | -8,4 [-9,4 ; -7,4] | -213 | -22,1 | 791 | -0,28 | < 0,001 | < 0,001 |
| `NAI-P-perd` (base) | probabiliste | côté perdant seul | Naïve | -10,9 [-12,0 ; -10,0] | -287 | -29,8 | 267 | -1,10 | < 0,001 | < 0,001 |
| `AS-P-perd` (base) | probabiliste | côté perdant seul | Avellaneda-Stoikov | -14,6 [-16,1 ; -13,2] | -287 | -29,8 | 267 | -1,10 | < 0,001 | < 0,001 |
| `ASP-P-perd` (base) | probabiliste | côté perdant seul | AS skew plafonné | -12,9 [-14,2 ; -11,8] | -288 | -29,8 | 268 | -1,09 | < 0,001 | < 0,001 |
| `GLFT-P-perd` (base) | probabiliste | côté perdant seul | GLFT | -15,0 [-16,5 ; -13,7] | -288 | -29,9 | 267 | -1,10 | < 0,001 | < 0,001 |
| `PLA-P-perd` (base) | probabiliste | côté perdant seul | Placebo | -10,6 [-11,7 ; -9,5] | -279 | -28,9 | 266 | -1,09 | < 0,001 | < 0,001 |
| `NAI-P-deux` | probabiliste | les deux côtés | Naïve | -3,4 [-4,4 ; -2,4] | -89 | -9,2 | 402 | -0,27 | < 0,001 | < 0,001 |
| `AS-P-deux` | probabiliste | les deux côtés | Avellaneda-Stoikov | -6,6 [-8,1 ; -5,4] | -110 | -11,4 | 399 | -0,28 | < 0,001 | < 0,001 |
| `ASP-P-deux` | probabiliste | les deux côtés | AS skew plafonné | -5,8 [-7,2 ; -4,7] | -106 | -11,0 | 400 | -0,27 | < 0,001 | < 0,001 |
| `GLFT-P-deux` | probabiliste | les deux côtés | GLFT | -7,1 [-8,8 ; -5,7] | -113 | -11,7 | 399 | -0,28 | < 0,001 | < 0,001 |
| `PLA-P-deux` | probabiliste | les deux côtés | Placebo | -3,6 [-4,7 ; -2,6] | -95 | -9,8 | 395 | -0,29 | < 0,001 | < 0,001 |

**Sensibilités Monte Carlo** (500 sessions par cellule, tirages communs ; Sharpe simulé d'Avellaneda-Stoikov ; tableaux complets et figures dans la section « Pourquoi un Sharpe de simulation n'est pas un Sharpe de marché ») :

| Paramètre balayé | Plage | Sharpe AS le plus bas | Sharpe AS le plus haut |
|---|---|---|---|
| sélection adverse p | 0,0 → 0,4 | 19,2 | 31,4 |
| latence (délai entre deux mises à jour des cotes) | 100 ms → 60 s | -99,2 | 25,3 |
| γ de la stratégie, à latence 100 ms | × 0,25 → × 4 autour de la base | 15,9 | 42,3 |
| A et k réels du marché (la stratégie garde ses croyances) | A de 0,05 à 0,20, k de 4,0 à 9,0 | 9,3 | 59,5 |
| p et k réel | p de 0,0 à 0,4, k de 4 à 10 | 12,0 | 38,0 |
<!-- /AUTO:VARIANTES -->

![Toutes les variantes : PnL cumulé net des 30 rejeux, cas de base en couleur](figures/toutes_variantes.png)

**Comment lire ce graphique.** Chaque ligne grise est le PnL cumulé net d'une des 25 variantes autres que le cas de base ; les cinq lignes en couleur (quasi superposées) sont le cas de base. L'éventail des PnL cumulés finaux va de -9,2 à -59,8 millions de USD : la convention de fill déplace l'ampleur de la perte (le groupe le plus bas est « côté perdant seul » avec f = 1, où chaque barre qui traverse la cote est exécutée et, par construction, du côté qui perd), jamais son signe.
Aucune courbe ne monte.

![Sharpe du rejeu réel contre Sharpe simulé pour les 30 variantes](figures/overfit_scatter.png)

**Comment lire ce graphique.** Un point par variante : Sharpe annualisé de la **simulation** en abscisse (le même pour les 6 variantes d'une stratégie), Sharpe du **rejeu sur marché réel** en ordonnée, avec son IC 95 % par blocs de 10 jours. Sur la diagonale, le réel ferait aussi bien que la simulation. Ici tous les points sont très en dessous, sous zéro : plein = côté perdant seul, creux = les deux côtés ; la forme est le modèle de fill.
Le « hors échantillon » de ce projet est le marché réel : c'est là que le Sharpe simulé s'effondre.

## Tableau de bord interactif

Choisissez vous-même les conditions de départ : **nombre d'exécutions minimum** et **Sharpe minimum** sur la période de sélection (2019-2020), stratégies, modèles de fill, convention. Seules les variantes qui passent ces filtres sont combinées (moyenne équipondérée) ; la courbe obtenue est affichée sur 2019-2020 puis sur 2021-2022 (évaluation), avec ses métriques recalculées et un voyant « Overfit ? ».

- En ligne : <https://yassine-ek.github.io/fx-market-making/>
- Ou ouvrir `docs/index.html` localement (les données sont dans `docs/data.js`, aucun serveur nécessaire ; sinon lancer `python -m http.server` dans `docs/`).
- Régénérer : `python scripts/exporter_dashboard.py` (lit `results/`, aucune donnée de marché requise).

**Lecture des libellés (adaptation honnête du gabarit commun).** Le gabarit commun affiche ici les noms des deux périodes grâce à son champ `libelles` : **« SÉLECTION 2019-2020 »** et **« ÉVALUATION 2021-2022 »**, les deux moitiés de VAL. Le rejeu ne couvre que VAL 2019-2022 ; cette coupure est un choix de présentation (frontières `train_fin = 2020-12-31`, `val_fin = 2022-12-31` dans `docs/data.json`), pas un second jeu de test : les 30 variantes sont fixées avant, et toutes ont un Sharpe négatif, donc aucun filtre ne peut créer d'edge, il montre ce que coûte la convention de fill.
Les rendements du tableau de bord sont le PnL net en USD divisé par un capital de référence arbitraire de 100 M USD (ne change pas le Sharpe). TEST 2023+ n'apparaît jamais.

## Pourquoi ce projet

- **XRAYS TRADING** (automates de trading algorithmique ; stages « système de Market Making directement exposé aux marchés » et « simulateur qui teste nos automates face aux marchés », d'après la page stage du site) :
  ce dépôt est un petit simulateur d'automate de market making testé face à des marchés synthétiques *et* réels : noyau à état déterministe à entrées pré-tirées
  (rejouable bit à bit, donc comparable à une implémentation C++), bornes d'inventaire comme contrôle de risque, tests d'identité comptable et de non-fuite, mesure d'écart simulation/réel.
- **smartTrade** (LiquidityFX : agrégation de liquidité FX, pricing dynamique « skewing / spreading », couverture automatique par règles d'inventaire du livre) :
  le décalage AS de la cote contre l'inventaire est un *skew*, la dépendance du spread à σ et γ est du *spreading*, et la borne Q joue le rôle du seuil de déclenchement d'un hedge
  (non codé ici). Je n'ai pas vu leur code : le rapprochement est conceptuel.

## Méthode

### Le problème du market maker

Un market maker affiche un bid et un ask autour du prix « juste » (le *mid*). Chaque exécution lui rapporte un petit écart
(la **capture de spread**) mais modifie son **inventaire** *q* (en lots ; 1 lot = 1 M EUR, donc 1 pip x 1 lot = 100 USD).
Si le prix part contre cette position, la perte dépasse les gains de spread. Tout le travail est cet arbitrage :

```
PnL = capture de spread + variation de valeur de l'inventaire - coût de liquidation - frais
```

Le simulateur calcule cette décomposition à chaque session, et un test vérifie que le PnL obtenu autrement
(`cash + inventaire x mid - liquidation`) coïncide avec la somme des composantes à 1e-9.

### Les stratégies comparées (`mm/modeles.py`)

| Stratégie | Idée | Formule (profondeur = distance de la cote au mid) |
|---|---|---|
| Naïve symétrique | spread fixe, aveugle à l'inventaire | δ = 1/k de chaque côté (limite risque-neutre d'AS) |
| Avellaneda-Stoikov (2008) | je décale mes cotes contre mon inventaire | r = s - q·γ·σ²·(T-t) ; spread = γσ²(T-t) + (2/γ)·ln(1+γ/k) |
| AS skew plafonné | idem, décalage borné | décalage ≤ 1/(2k) : le côté à réduire garde la moitié de son demi-spread |
| GLFT (Guéant-Lehalle-Fernandez-Tapia, 2013) | solution asymptotique (horizon long, inventaire borné par Q) | δ_b = c1 + (q+½)·c2, δ_a = c1 - (q-½)·c2 ; c1 = ln(1+γ/k)/γ, c2 = √(γσ²/(2Ak)·(1+γ/k)^(1+k/γ)) |
| Placebo | cotes aléatoires de même largeur moyenne que AS (0,175 pip de demi-spread) | δ_b, δ_a ~ U(0, 2m), indépendantes du prix et de l'inventaire |

**γ n'a pas la même unité dans AS et GLFT** (AS le multiplie par T-t, jusqu'à 32 400 s ; GLFT est stationnaire). On n'égalise donc pas γ :
on fixe un **critère d'agressivité commun, choisi a priori** (à Q/2 lots d'inventaire, la cote est décalée de 1/k pip), ce qui donne
γ_AS = 9,46e-06 et γ_GLFT = 1,13e-03. Aucun paramètre n'est optimisé sur les résultats.
Toutes les stratégies sont soumises à la même borne d'inventaire Q = 20 lots (une cote est retirée côté renforçant la position extrême).

### Le simulateur (`mm/simulateur.py`)

Pas de temps dt = 0,1 s sur une session de 9 h (03h-12h heure de New York, 324 000 pas). Mid = mouvement brownien arithmétique de volatilité σ.
À chaque pas :

1. toutes les `L` périodes, les cotes (prix absolus) sont recalculées depuis le mid courant ; **entre deux mises à jour elles sont périmées** (latence) ;
2. exécution côté bid puis ask avec probabilité 1-exp(-λ·dt), λ = A·exp(-k·δ), δ mesuré au mid *courant* ;
3. **sélection adverse** : après une exécution, avec probabilité p le mid saute de α contre le market maker (flux informé) ;
4. diffusion du mid : dS = σ√dt·N(0,1) ;
5. en fin de session, liquidation de l'inventaire résiduel au mid ± demi-spread de marché.

Tous les nombres aléatoires d'une session sont tirés *avant* par `np.random.default_rng([graine, indice_de_session])` et passés au noyau numba :
la reproductibilité est celle de numpy, et **toutes les stratégies voient exactement les mêmes sessions** (nombres aléatoires communs :
un écart entre deux stratégies vient de leur logique, pas de la chance). Le noyau est un automate à état simple (inventaire, cotes, horloge) :
c'est la forme qu'on retrouve dans un simulateur d'automates de trading.

### Données et hypothèses

Données : EURUSD 1 minute HistData (prix **BID**, heure locale de New York avec heure d'été, volume nul : malgré la documentation « EST sans DST », le pic NFP de 8h30 est à 8h30 l'été comme l'hiver). Split imposé : **TRAIN ≤ 2018** (calibration de σ uniquement),
**VAL 2019-2022** (rejeu), **TEST 2023+ scellé** : `mm/donnees.py` refuse de le lire (`PermissionError`, testé).

| Paramètre | Valeur | Statut |
|---|---|---|
| sigma (pips / √s) | 0,330 | MESURÉ sur TRAIN 2010-2018, 03h-12h heure de New York |
| A (exécutions / s à profondeur 0, par côté) | 0,10 | hypothèse |
| k (1/pip) | 6,0 | hypothèse |
| demi-spread de marché (pip) | 0,10 | hypothèse (EURUSD interbancaire ≈ 0,1-0,3 pip de spread) |
| p (proba de saut après exécution) | 0,20 | hypothèse |
| alpha (taille du saut, pip) | 0,30 | hypothèse |
| frais (pip / exécution) | 0,005 | hypothèse |
| Q (borne d'inventaire, lots) | 20 | choix de conception |
| pas de temps dt | 0,1 s | choix de conception |
| durée de session | 9 h (03h-12h heure de New York) | choix de conception |

**A, k, p, α, le spread et les frais ne sont pas mesurés** : on n'a pas de données d'ordres, seulement des barres. Ce sont des hypothèses
fixées *avant* de voir les résultats, avec une analyse de sensibilité (grille 3x3 pour A et k, balayages de p et de la latence). Les chiffres
du Monte Carlo sont donc **conditionnels** à ces hypothèses. σ = 0,330 pip/√s (soit 2,55 pips par minute : une barre de
1 minute bouge d'environ 15 demi-spreads, ce qui compte pour le rejeu).

![sigma par heure](figures/sigma_par_heure.png)

**Comment lire ce graphique.** Volatilité réalisée de l'EURUSD par heure de New York, mesurée sur TRAIN 2010-2018 (variations de close entre minutes consécutives). Les barres bleues sont les heures de la session simulée (03h-12h) : c'est leur moyenne en variance qui donne σ. La volatilité monte entre 02h et 03h (ouverture de Londres) et culmine entre 08h et 09h (annonces américaines de 8h30).

## Résultats détaillés

Tous les chiffres ci-dessous sont lus dans `results/verdict_mm.json` et `results/rejeu_variantes.json` (ce fichier README est généré par `scripts/generer_readme.py`).

### Monte Carlo (2 000 sessions de 9 h par stratégie, graines communes)

| Stratégie | Sharpe annualisé | IC95 bootstrap | PnL moyen (pips x lot) | écart-type | P(perte) | CVaR 5 % | inventaire max (moy. / p95) | exécutions |
|---|---|---|---|---|---|---|---|---|
| Naïve symétrique | 7,0 | [6,3 ; 7,8] | 298 | 675 | 32,5 % | -1 128 | 20,0 / 20 | 2 325 |
| Avellaneda-Stoikov | 25,0 | [23,9 ; 26,0] | 302 | 192 | 5,7 % | -92 | 14,1 / 20 | 2 319 |
| AS skew plafonné | 24,7 | [23,7 ; 25,8] | 303 | 194 | 5,6 % | -95 | 14,2 / 20 | 2 315 |
| GLFT asymptotique | 36,0 | [34,8 ; 37,3] | 306 | 135 | 0,8 % | 40 | 7,9 / 9 | 2 320 |
| Placebo (cotes aléatoires) | 5,7 | [5,0 ; 6,4] | 246 | 687 | 36,2 % | -1 183 | 20,0 / 20 | 2 637 |

Sharpe journalier annualisé par √252 ; IC95 par bootstrap des sessions ; CVaR 5 % = moyenne des 5 % pires journées.
Décomposition du PnL moyen (pips x lot par session) :

| Stratégie | capture de spread | inventaire : diffusion | inventaire : sélection adverse | liquidation | frais | = PnL moyen |
|---|---|---|---|---|---|---|
| Naïve symétrique | 388 | -2 | -75 | -1,1 | -12 | 298 |
| Avellaneda-Stoikov | 387 | 0 | -72 | -0,8 | -12 | 302 |
| AS skew plafonné | 387 | 0 | -72 | -0,8 | -12 | 303 |
| GLFT asymptotique | 387 | 1 | -70 | -0,2 | -12 | 306 |
| Placebo (cotes aléatoires) | 311 | 33 | -85 | -1,0 | -13 | 246 |

![distributions](figures/distributions_pnl.png)

**Comment lire ce graphique.** Un histogramme par stratégie du PnL d'une session de 9 h (2 000 sessions, mêmes tirages pour toutes). Le trait noir est la moyenne, le pointillé rouge le zéro. Les moyennes sont presque égales ; ce qui change, c'est la largeur : le naïf et le placebo ont des queues de perte profondes, AS et GLFT sont resserrés autour de la moyenne.

![decomposition](figures/decomposition_pnl.png)

**Comment lire ce graphique.** Pour chaque stratégie, les composantes du PnL moyen par session (barres) et leur somme (losange noir). La capture de spread (la grande barre positive) est quasi identique partout ; la sélection adverse retire environ un cinquième ; la liquidation et les frais sont petits. Les stratégies ne diffèrent donc pas par ce qu'elles gagnent mais par le risque d'inventaire qu'elles portent.

![trajectoire](figures/trajectoire_exemple.png)

**Comment lire ce graphique.** Haut : deux minutes d'une session simulée d'AS, avec le mid, les cotes bid/ask (en escalier, car recalculées par pas de 0,1 s) et les exécutions (triangles). Milieu : l'inventaire correspondant. Bas : l'inventaire de la session entière pour les cinq stratégies, mêmes tirages ; le naïf et le placebo atteignent la borne de 20 lots (inventaire maximal moyen 20,0), AS et surtout GLFT la contiennent bien mieux (14,1 et 7,9 lots).

À lire : la **capture de spread est à peu près la même pour tout le monde** (mêmes clients) ; ce qui change, c'est le **risque** d'inventaire.
AS et GLFT divisent l'écart-type des sessions par 3 à 5 par rapport au naïf, d'où un Sharpe de simulation bien supérieur. Le **placebo**
(cotes aléatoires de même largeur) a un Sharpe de 5,7, comparable au naïf (7,0) : le gain d'AS/GLFT vient de la
logique d'inventaire, pas de la largeur des cotes. Mais **dans un monde simulé qui obéit exactement au modèle testé, cette supériorité est
une propriété de la simulation, pas une preuve de performance**.

### Rejeu sur barres 1 minute réelles, VAL 2019-2022 (1036 journées de Londres)

Règles (voir `mm/rejeu_reel.py`) : référence causale = close de la minute précédente (+ demi-spread de marché, HistData étant en BID) ; la
cote de la minute *i* n'utilise que des données ≤ *i*-1 (test de non-fuite : on modifie les barres futures, les cotes passées ne bougent pas) ;
le bid n'est exécuté que si la barre suivante **traverse** la cote ; si bid et ask sont tous deux atteints, on suppose l'**ordre défavorable**
(le côté qui perd passe d'abord). Trois modèles de fill : « toucher suffit », « traverser d'au moins 0,1 pip », « traverser de 0,1 pip **et**
tirer la probabilité de file f = 0,5 ». Et deux lectures du cas « bid ET ask touchés » qui encadrent la vérité : **seul le côté perdant est exécuté**
(pessimiste) ou **les deux côtés le sont** (optimiste, aller-retour à chaque barre). Cas de base : *probabiliste (traversée >= 0,1 pip, f = 0,50)*, côté perdant seul (volontairement pessimiste : dans chaque barre où bid et ask sont atteints, le fill défavorable est le seul retenu).

**Sharpe annualisé du rejeu selon le modèle de fill** (le message central de cette section) :

| modèle de fill (traversée, f) | bid ET ask touchés | Naïve | Avellaneda-Stoikov | AS skew plafonné | GLFT | Placebo |
|---|---|---|---|---|---|---|
| touche (0,0 pip, f = 1,00) | seul le côté perdant (pessimiste) | -17,8 | -22,8 | -20,4 | -23,2 | -17,4 |
| touche (0,0 pip, f = 1,00) | les deux côtés (optimiste) | -5,5 | -13,5 | -13,3 | -16,2 | -5,9 |
| traversee (0,1 pip, f = 1,00) | seul le côté perdant (pessimiste) | -17,6 | -22,4 | -20,4 | -22,9 | -17,5 |
| traversee (0,1 pip, f = 1,00) | les deux côtés (optimiste) | -7,9 | -17,5 | -17,0 | -20,9 | -8,4 |
| probabiliste (0,1 pip, f = 0,50) | seul le côté perdant (pessimiste) | -10,9 | -14,6 | -12,9 | -15,0 | -10,6 |
| probabiliste (0,1 pip, f = 0,50) | les deux côtés (optimiste) | -3,4 | -6,6 | -5,8 | -7,1 | -3,6 |

![modeles de fill](figures/rejeu_modeles_fill.png)

**Comment lire ce graphique.** Pour chaque stratégie (axe horizontal), trois barres = les trois modèles de fill (de plus en plus foncé : touche, traversée, probabiliste), avec leur IC 95 % par blocs de 10 jours. À gauche la convention « côté perdant seul », à droite « les deux côtés ». Toutes les barres sont sous zéro ; ce qui les fait varier, c'est le modèle de fill et la convention, pas la stratégie.

Trois constats.

1. **Aucune des six conventions ne donne un Sharpe positif** (de -23,2 à -3,4). La simulation, elle, donnait +7,0 à +36,0.
2. **Seule la probabilité de file f change vraiment le résultat.** Exiger une traversée de 0,1 pip plutôt que 0 est presque sans effet (voir la figure ci-dessous) : une barre d'une minute bouge d'environ 2,55 pips, soit une quinzaine de demi-spreads, donc nos cotes sont
   traversées de toute façon. Plus f est grand, plus on est exécuté, donc plus on perd.
3. **Le classement en Sharpe s'inverse** : AS et GLFT font moins bien que le naïf sous les six conventions, alors qu'ils le dominaient en simulation.
   Deux effets mêlés, non démêlés : (i) quand l'espérance est négative, réduire la variance (ce que fait AS) rend le Sharpe plus négatif ; (ii) sous « deux côtés »,
   le PnL *moyen* d'AS est lui aussi plus bas. Hypothèse (non testée) pour (ii) : le décalage d'inventaire rapproche la cote du mid, donc sacrifie une partie de
   l'edge, pour un bénéfice de risque qui ne se paie pas quand chaque exécution est déjà adverse.

![sensibilité à f et au seuil](figures/rejeu_sensibilite_f_seuil.png)

**Comment lire ce graphique.** Sharpe du rejeu d'AS pour chaque couple (probabilité de file f en abscisse, traversée exigée en ordonnée, de −0,1 à +0,3 pip ; une traversée négative n'exige même pas que le mid atteigne la cote). Les cases d'une même colonne sont presque identiques : le seuil compte peu, f décide.

Le cas de base, avec **IC95 par bootstrap en blocs de 10 jours** (les PnL journaliers réels peuvent être autocorrélés ; l'IC « iid » est donné pour comparaison) :

| Stratégie | Sharpe | IC95 par blocs de 10 j | IC95 iid (trop étroit) | PnL moyen / jour | exécutions / jour | inventaire max moyen |
|---|---|---|---|---|---|---|
| Naïve symétrique | -10,9 | [-12,0 ; -10,0] | [-12,0 ; -10,0] | -287 | 267 | 16,4 |
| Avellaneda-Stoikov | -14,6 | [-16,1 ; -13,2] | [-16,0 ; -13,3] | -287 | 267 | 13,0 |
| AS skew plafonné | -12,9 | [-14,2 ; -11,8] | [-14,1 ; -11,8] | -288 | 268 | 14,0 |
| GLFT asymptotique | -15,0 | [-16,5 ; -13,7] | [-16,4 ; -13,8] | -288 | 267 | 12,4 |
| Placebo (cotes aléatoires) | -10,6 | [-11,7 ; -9,5] | [-11,6 ; -9,5] | -279 | 266 | 16,3 |

![PnL cumulé](figures/rejeu_val_pnl_cumule.png)

**Comment lire ce graphique.** PnL cumulé de chaque stratégie (en pips × lot, 100 USD par unité) dans le modèle de base, côté perdant seul à gauche et les deux côtés à droite ; le total final est dans la légende. Les cinq courbes sont quasi superposées et décroissent régulièrement (environ -287 pips x lot par jour dans le cas de base, côté perdant seul) : la perte ne vient
pas d'une période particulière mais de la convention elle-même.

**Markout** : pour chaque exécution, (mid futur - prix d'exécution) x sens, à +1, +5 et +15 minutes (pips par exécution, ± IC95 ; modèle de base,
lecture « deux côtés » pour ne pas mélanger l'artefact du choix du côté perdant) :

| Stratégie | +1 min | +5 min | +15 min |
|---|---|---|---|
| Naïve symétrique | -0,27 ± 0,01 | -0,26 ± 0,01 | -0,27 ± 0,02 |
| Avellaneda-Stoikov | -0,28 ± 0,01 | -0,28 ± 0,01 | -0,28 ± 0,02 |
| AS skew plafonné | -0,27 ± 0,01 | -0,27 ± 0,01 | -0,28 ± 0,02 |
| GLFT asymptotique | -0,28 ± 0,01 | -0,28 ± 0,01 | -0,29 ± 0,02 |
| Placebo (cotes aléatoires) | -0,29 ± 0,01 | -0,28 ± 0,01 | -0,29 ± 0,02 |

![markout](figures/markout_rejeu.png)

**Comment lire ce graphique.** Markout moyen par exécution à +1, +5 et +15 minutes (une barre par stratégie), avec son IC 95 %. Une sélection adverse « réelle » donnerait un markout de plus en plus négatif avec l'horizon ; ici les trois horizons sont au même niveau : rien ne suit l'exécution.

Le markout est négatif et **constant de +1 à +15 minutes** : rien ne « suit » l'exécution, le prix ne revient pas mais ne s'éloigne pas non plus. L'edge
théorique d'une exécution (le demi-spread posé, environ 0,17 pip) est pourtant plus que mangé, et **ce n'est pas une mesure de la sélection adverse du marché
réel** : une barre qui traverse notre cote est, par construction, une barre qui bouge, et l'exécution est comptée au prix de la cote alors que le prix a déjà
dépassé la cote (traversée exigée de 0,1 pip + dépassement à l'intérieur de la barre). Contrôle : le même rejeu appliqué à 400 journées d'une marche
aléatoire **sans dérive et sans sélection adverse**, de même sigma de minute que VAL (1,89 pips), donne des résultats du même ordre de grandeur (plus négatifs côté perdant seul, quasi identiques côté deux côtés) :

| bid ET ask touchés | Stratégie | PnL moyen/jour : barres réelles | PnL moyen/jour : marche aléatoire | markout +1 min : barres réelles | markout +1 min : marche aléatoire |
|---|---|---|---|---|---|
| seul le côté perdant | Naïve symétrique | -287 | -359 | -1,10 | -1,33 |
| seul le côté perdant | Avellaneda-Stoikov | -287 | -361 | -1,10 | -1,33 |
| les deux côtés | Naïve symétrique | -89 | -97 | -0,27 | -0,24 |
| les deux côtés | Avellaneda-Stoikov | -110 | -106 | -0,28 | -0,25 |

Le rejeu ne distingue donc pas l'EURUSD réel d'une marche aléatoire : son résultat mesure le coût de la **convention de fill**, pas une propriété de la microstructure réelle.
Il montre que la simulation (Sharpe positif) et le rejeu sur barres (Sharpe négatif) ne se comparent pas, pas que le marché réel punit ces stratégies.

**Placebo dans le rejeu** (30 graines de tirages, mêmes graines pour AS et pour le placebo ; cotes aléatoires de même largeur moyenne) :

| bid ET ask touchés | Sharpe AS | Sharpe placebo | PnL moyen/jour AS | PnL moyen/jour placebo | AS > placebo (Sharpe) | AS > placebo (PnL moyen) |
|---|---|---|---|---|---|---|
| seul le côté perdant | -14,7 | -10,6 (5e-95e pct : -11,2 ; -10,0) | -288 | -279 | 0 % des graines | 13 % des graines |
| les deux côtés | -7,0 | -4,1 (5e-95e pct : -4,8 ; -3,4) | -114 | -106 | 0 % des graines | 20 % des graines |

![placebo](figures/placebo_rejeu.png)

**Comment lire ce graphique.** Pour chaque lecture de « bid ET ask touchés » (une colonne), le Sharpe (haut) et le PnL moyen par jour (bas) obtenus pour chacune des 30 graines de tirage, pour AS (bleu) et pour le placebo (violet). Les deux distributions se chevauchent presque en PnL moyen (aucun avantage d'AS), alors que le Sharpe d'AS est systématiquement plus négatif (moins de variance).

Dans le rejeu, **AS n'a aucun avantage d'espérance sur des cotes tirées au hasard** : PnL moyen par jour de -288 contre -279
(côté perdant seul) et -114 contre -106 (deux côtés) ; AS ne fait mieux que le placebo dans 13 % et 20 %
des graines seulement. AS réduit bien la variance (écart-type journalier 313 contre 419 pips x lot dans le cas de base),
mais quand l'espérance est négative, **réduire la variance dégrade le Sharpe** : c'est pourquoi AS est plus négatif que le placebo en Sharpe dans 100 % des graines.
Comparer des Sharpe sans regarder les espérances aurait donné une conclusion trompeuse. La logique d'inventaire d'AS, précieuse dans le monde simulé, ne produit
aucun gain d'espérance sur ces barres.

### Pourquoi un Sharpe de simulation n'est pas un Sharpe de marché

Trois mécanismes, absents du modèle de base, sont chacun suffisants pour détruire le Sharpe simulé.

**Sélection adverse** : p = 0 → p = 0,4 fait passer AS de 31,4 à 19,2. La baisse est régulière mais modérée tant que
p·α (perte moyenne par exécution) reste sous le demi-spread.

| p (sélection adverse) | Naïve | Avellaneda-Stoikov | AS skew plafonné | GLFT | Placebo |
|---|---|---|---|---|---|
| 0,00 | 8,8 | 31,4 | 31,1 | 43,5 | 7,9 |
| 0,10 | 7,8 | 28,2 | 27,9 | 39,4 | 6,9 |
| 0,20 | 6,9 | 25,3 | 25,0 | 35,3 | 5,9 |
| 0,30 | 6,1 | 22,2 | 22,0 | 31,0 | 4,9 |
| 0,40 | 5,3 | 19,2 | 19,0 | 26,9 | 3,9 |

**Latence (cotes périmées)** : le mid bouge de σ√(L·dt) entre deux mises à jour ; dès que ce mouvement dépasse le demi-spread, les cotes se font
« ramasser ». AS passe de 25,3 (100 ms) à -3,2 à 1 s et -99,2 à 60 s.

| délai entre deux mises à jour des cotes | Naïve | Avellaneda-Stoikov | AS skew plafonné | GLFT | Placebo |
|---|---|---|---|---|---|
| 100 ms | 6,9 | 25,3 | 25,0 | 35,3 | 5,9 |
| 200 ms | 5,5 | 21,3 | 21,0 | 27,6 | 4,1 |
| 500 ms | 2,9 | 9,7 | 9,6 | 12,9 | 1,6 |
| 1 s | -1,2 | -3,2 | -2,8 | -4,2 | -1,9 |
| 3 s | -11,0 | -25,9 | -23,2 | -33,9 | -11,4 |
| 10 s | -31,7 | -52,3 | -44,0 | -59,8 | -30,6 |
| 60 s | -85,1 | -99,2 | -91,3 | -101,2 | -84,4 |

![effondrement du Sharpe](figures/sharpe_effondrement.png)

**Comment lire ce graphique.** Sharpe simulé de chaque stratégie quand on augmente la part de flux informé p (à gauche) puis le délai entre deux mises à jour des cotes (à droite, échelle logarithmique). Le Sharpe baisse doucement avec p, mais passe sous zéro entre 0,5 et 1 s de latence et devient très négatif à 60 s : le rejeu sur barres 1 minute est dans cette zone.

**Le rejeu sur barres 1 minute équivaut à coter avec 60 s de latence** : la cote posée au close précédent reste fixe pendant une minute où le prix bouge de
2,55 pips. Le rejeu tombe dans la zone « effondrée » de la figure ci-dessus. Il ne peut donc **pas** valider un market maker à
haute fréquence ; il sert à mesurer l'écart avec la simulation et la sensibilité aux conventions de fill.

**Sensibilité aux hypothèses A, k et au gamma de la stratégie** (cases en gras = valeurs de base ; k réel ≠ k supposé par la stratégie) :

![heatmap p x k](figures/heatmap_p_k.png)

**Comment lire ce graphique.** Sharpe simulé d'AS pour chaque couple (k réel du marché en abscisse, probabilité de sélection adverse p en ordonnée) alors que la stratégie croit k = 6 ; la case en gras est le cas de base. Rouge = négatif, bleu = positif. Le Sharpe reste positif sur toute la grille (de 12,0 à 38,0) : p et k seuls n'expliquent pas le rejeu.

![heatmap latence x gamma](figures/heatmap_latence_gamma.png)

**Comment lire ce graphique.** Sharpe simulé d'AS selon le gamma de la stratégie (de ×0,25 à ×4, en abscisse) et la latence (en ordonnée). À faible latence, un gamma plus grand (plus de contrôle d'inventaire) augmente le Sharpe simulé ; à partir de 1 s de latence il est négatif quel que soit gamma : on ne rattrape pas des cotes périmées en ajustant l'aversion au risque.

![heatmap A x k](figures/heatmap_A_k.png)

**Comment lire ce graphique.** Une grille 3×3 par stratégie : Sharpe simulé quand A (fréquence d'exécution) et k (sensibilité à la profondeur) réels diffèrent des croyances de la stratégie (case en gras = hypothèses de base). Les Sharpe changent d'ampleur (de 1,1 à 81,8 sur toute la grille et toutes les stratégies) mais restent positifs.

Ces grilles sont une **présentation de robustesse, pas une optimisation** : 3x3 pour A et k, 5x5 au plus pour les autres, et aucune valeur n'est
retenue en fonction du résultat.

## Validation et tests

63 tests, quelques secondes (`python -m pytest -q`) ; chaque brique est confrontée à une réponse connue.

- **Comptabilité** : le PnL obtenu autrement (`cash + inventaire x mid - liquidation`) coïncide avec la somme des composantes à 1e-9, en simulation et dans le rejeu, pour toutes les stratégies et conventions.
- **Cas limites exacts** : avec σ = 0 et p = 0, le PnL est exactement (demi-spread posé) × (nombre d'exécutions) moins la liquidation ; l'inventaire ne dépasse jamais la borne Q ; mêmes graines = mêmes résultats, graines différentes = résultats différents.
- **Non-fuite** : modifier les barres futures ne change aucune cote passée du rejeu ; le TEST 2023+ lève `PermissionError` à la lecture.
- **Formules** : AS, GLFT, prix de réservation et constantes c1, c2 contre leurs expressions fermées ; σ retrouvé à quelques pour cent sur des barres synthétiques, sans fabriquer de volatilité avec les trous.
- **Rejeu** : fills (traversée de 0,1 pip, probabilité de file, ordre défavorable) vérifiés sur des barres écrites à la main ; markout recalculé à la main ; contrôle marche aléatoire (le markout négatif y apparaît déjà) ; fuseau (réouverture hebdomadaire à 17h00 en juillet comme en janvier, sur les données réelles).
- **Significativité** : PSR et DSR contre des valeurs connues (Sharpe nul, grand échantillon, nombre d'essais croissant).
- **Cohérence des sorties** : le PnL quotidien exporté redonne exactement le Sharpe de `results/verdict_mm.json` pour les 30 variantes ; `docs/data.json` est cohérent avec `results/` et ne contient aucune date ≥ 2023 ; les blocs de chiffres du README sont à jour ; aucun chemin absolu de machine dans le dépôt.
- **Relecture adversariale du 13/10** (agent indépendant, voir `_revue/` du portfolio) : réimplémentation Python pure du rejeu (mêmes exécutions et mêmes PnL en mode « deux côtés », à 4e-10), contrôle marche aléatoire ajouté après avoir montré que le markout négatif n'était pas une mesure de la sélection adverse, description du fuseau corrigée (aucun chiffre existant n'a changé).

## Limites (dites franchement)

- **A, k, p, α, spread et frais sont des hypothèses**, pas des mesures (aucune donnée d'ordres). Le Monte Carlo est conditionnel à elles.
- Le monde simulé **obéit au modèle** testé (mouvement brownien, intensités exponentielles) : la supériorité d'AS/GLFT sur le naïf y est presque tautologique.
- Fills de Poisson **indépendants du prix** hors sélection adverse : c'est vraisemblablement une borne haute ; le rejeu sur barres, où chaque fill est conditionné au mouvement du prix, est vraisemblablement une borne basse (ni l'une ni l'autre n'est démontrée). La vérité est probablement entre les deux, et on ne sait pas où.
- Rejeu sur barres 1 minute : pas de carnet L2, pas de position dans la file (seulement un facteur f), 1 lot par exécution, pas d'impact, **60 s de latence implicite**, un demi-spread de marché constant ajouté à des prix BID, ordre intra-barre inconnu.
- σ constant dans la session (pas de saisonnalité intra-session ni de sauts hors sélection adverse) ; session 03h-12h heure de New York = 08h-17h Londres toute l'année sauf ~3 semaines par an où les heures d'été US et européenne diffèrent (décalage d'1 h non corrigé).
- Un seul actif (EURUSD), pas de hedge actif de l'inventaire ni de multi-fournisseurs de liquidité.
- VAL seul est lu, le TEST reste scellé : aucun verdict out-of-sample final n'est prétendu. Le DSR est calculé sur les 30 variantes du rejeu (tous les Sharpe sont négatifs, donc le DSR est nul) ; il ne couvre ni les balayages Monte Carlo ni les choix de conception, et les IC du rejeu ne corrigent pas le nombre d'essais.
- Le tableau de bord coupe VAL en deux moitiés (sélection 2019-2020, évaluation 2021-2022) : c'est un exercice de présentation, pas un second hors-échantillon indépendant (l'auteur a vu toute la période VAL) ; les rendements y sont rapportés à un capital de référence arbitraire.
- Les IC bootstrap supposent des sessions indépendantes en simulation (vrai par construction) et des blocs de 10 jours dans le rejeu (choix a priori, non optimisé).

## Positionnement face aux dépôts GitHub

D'après une recherche du 13/10/2026 (71 dépôts de market making, microstructure et exécution ; README lus, code non exécuté ; voir `projets_cv/_recherche/github_marketmaking.md`) :

| Dépôt | Ce que c'est | Ce que ce projet apporte en plus |
|---|---|---|
| [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) | backtester Rust/Numba sur carnet L2/L3 avec latence de flux, latence d'ordre et file d'attente | FX sur barres 1 min, markout, placebo, IC par blocs ; *eux* modélisent la file et la latence, *moi* je les traite en sensibilité |
| [JJJerome/mbt_gym](https://github.com/JJJerome/mbt_gym) | environnements gym vectorisés AS / Cartea-Jaimungal / exécution, avec solutions analytiques | calibration de σ sur données réelles, rejeu hors échantillon, split temporel strict |
| [cuemacro/tcapy](https://github.com/cuemacro/tcapy) | TCA FX spot (slippage, markout, benchmarks) | markout intégré à un simulateur de cotation (tcapy mesure, ne cote pas) |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | moteur événementiel de production, même code backtest/live, modèles de fill et de latence | périmètre volontairement réduit : le sujet ici est la validité du Sharpe, pas l'infrastructure |
| [abides-sim/abides](https://github.com/abides-sim/abides) | simulation multi-agents avec latences réseau | flux de fond synthétique remplacé par un modèle de flux informé à 2 paramètres (p, α) et des barres réelles |
| [fedecaccia/avellaneda-stoikov](https://github.com/fedecaccia/avellaneda-stoikov) | implémentation Python simple d'AS, fills de Poisson et paramètres (γ, σ, k) posés à la main, prix simulé | comparaison à GLFT, naïf et placebo ; sélection adverse et latence ; critère d'agressivité commun plutôt qu'un γ posé à la main (A et k sont aussi des hypothèses ici, mais avec grille de sensibilité) |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | framework de bots (pure MM, AS), orienté exploitation crypto, peu de mesure d'adverse selection d'après la note de recherche | markout par exécution et placebo ; pas de connecteurs ni de live |
| [DrAshBooth/PyLOB](https://github.com/DrAshBooth/PyLOB) | carnet d'ordres Python, hypothèse de latence nulle annoncée dans son README | latence et cotes périmées explicites |

Lacunes récurrentes relevées dans ces dépôts, que ce projet traite : latence et file d'attente absentes ou posées à la main ; fills « de Poisson » sans exiger que le
prix traverse la cote ; **pas de markout** (un seul dépôt sur la vingtaine de market making examinés l'annonce) ; pas de split TRAIN/VAL/TEST ni de validation sur données
réelles ; **pas d'IC ni de placebo**. Le FX est quasi absent de cet écosystème (le seul dépôt explicitement « FX market making » repéré a un README d'une ligne).
Ce que ce projet **n'a pas** : carnet L2, modèle de file d'attente, apprentissage par renforcement, code live, multi-actifs.

## Reproduire

```bash
pip install -r requirements.txt

# 1. Sans données de marché : tests, puis tout ce qui se régénère depuis results/
python -m pytest -q                        # les tests qui lisent les données sont sautés (« skipped »)
python scripts/exporter_dashboard.py       # -> docs/data.json, docs/data.js
python scripts/generer_figures_vitrine.py  # -> figures/hero_equity.png, toutes_variantes.png, overfit_scatter.png
python scripts/generer_readme.py           # -> README.md entier, chiffres lus dans results/

# 2. Avec les données HistData (non redistribuées) : définir HISTDATA_DIR
export HISTDATA_DIR=/chemin/vers/donnees   # PowerShell : $env:HISTDATA_DIR = "D:/donnees"
#   HISTDATA_DIR/histdata_raw/EURUSD/EURUSD_<année>.zip   minutes HistData (BID), 2010 à 2022 ; le TEST 2023+ n'est jamais lu
# Sans la variable, le défaut est ./data/histdata (ignoré par git).
python -m pytest -q                        # suite complète
python scripts/run_all.py                  # tout recalculer (quelques minutes) ; --rapide : 1 minute, écrit dans des sous-dossiers _rapide
python scripts/exporter_pnl_rejeu.py       # seulement le PnL quotidien des 30 variantes (~10 s) -> results/rejeu_*.csv et rejeu_variantes.json
python scripts/construire_notebook.py && python -m jupyter nbconvert --to notebook --execute --inplace notebooks/visite_guidee.ipynb
```

Graines : 20260713 (Monte Carlo), 777 (sensibilités), 20260714 (rejeu) ; les sessions sont indexées, donc 2 000 sessions = les mêmes 2 000 sessions à chaque relance.
Les données de marché ne sont pas redistribuées : sans elles on relit tous les chiffres dans `results/` et on régénère tout le reste (figures, tableau de bord, README), mais on ne rejoue pas le calcul.
Dépendances : Python 3.12+, numpy, numba, scipy, pandas, matplotlib, pytest ; nbformat, nbconvert et ipykernel seulement pour fabriquer et exécuter le carnet.

## Structure du dépôt

```
.
├── README.md                    ce fichier : frais, métriques simulation | rejeu, courbe finale, lecture « overfit ou pas ? »
├── LICENSE  requirements.txt  pytest.ini  conftest.py  .gitignore  .github/workflows/tests.yml
├── mm/                          le paquet : formules, simulateur numba, Monte Carlo, rejeu, 30 variantes, PSR/DSR, figures
├── scripts/                     calcul complet, export du PnL quotidien et du tableau de bord, figures vitrine, génération du README et du carnet
├── tests/                       suite pytest (synthétique, sauf les tests qui lisent les données locales)
├── notebooks/                   visite guidée : intuition → formule → attente → code → lecture
├── results/                     sorties figées (JSON, CSV du PnL quotidien) dont sont tirés tous les chiffres
├── figures/                     images du README (héro, toutes variantes, scatter, Monte Carlo, rejeu)
└── docs/                        tableau de bord interactif (GitHub Pages) : index.html + data.json + data.js
```

Chaque dossier a son propre `README.md` (rôle et une ligne par fichier).

---

## English summary

> 1. FX market-making simulator (numba core, seeded `default_rng` draws): naive quotes, Avellaneda-Stoikov (2008), capped-skew AS, GLFT (2013), random-quote placebo.
> 2. Poisson fills A·exp(-k·δ), adverse-selection jumps, stale-quote latency; PnL split into spread capture / inventory / liquidation / fees, identity tested to 1e-9.
> 3. Monte Carlo (2 000 sessions, common random numbers): annualised Sharpe with bootstrap CIs; simulated Sharpe is high (AS 25,0) but collapses with adverse selection and latency.
> 4. Replayed on real EURUSD 1-minute bars (VAL 2019-2022, TEST sealed) under three fill models and two bid-and-ask conventions: Sharpe is negative everywhere (-23,2 to -3,4). All 30 variants (5 strategies x 3 fill models x 2 conventions) are published, with a PSR/DSR and an interactive dashboard.
> 5. Markout at +1/+5/+15 min is negative and flat, but a driftless random-walk control reproduces it (it measures the fill convention, not real adverse selection); a block-bootstrap CI and a placebo (random quotes) show AS has no edge over chance on bars.
> 6. Take-away: a simulated Sharpe is an upper bound, not a market Sharpe. Limits: A, k, p, α are assumptions (no order data); 1-minute bars imply ~60 s quote refresh; no L2 book or queue model.
