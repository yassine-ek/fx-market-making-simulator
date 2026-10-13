# Projet 02 : un market maker FX qui gagne en simulation et perd en rejeu, et pourquoi

Simulateur de market making FX (Avellaneda-Stoikov, GLFT, naïf, placebo) avec noyau numba, Monte Carlo à tirages communs et rejeu sur barres EURUSD 1 minute réelles. L'objectif n'est pas de « battre le marché » : c'est de **montrer d'où vient le PnL d'un market maker, et combien de ce PnL est un artefact du simulateur**.

*An FX market-making simulator (Avellaneda-Stoikov, GLFT, naive quotes, random-quote placebo) with a Monte Carlo engine and a replay on real EURUSD 1-minute bars: the simulated Sharpe is an upper bound, and a random-walk control shows that the replay measures the fill convention, not the market.*

![tests](https://img.shields.io/badge/tests-<<n_tests>>%20passed-brightgreen) ![python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue) ![licence](https://img.shields.io/badge/licence-MIT-lightgrey)

<!-- AUTO:TETE -->
<<bloc_tete>>
<!-- /AUTO:TETE -->

![PnL cumulé net de frais du rejeu VAL pour les 5 stratégies, cas de base, avec drawdown en dessous](figures/hero_equity.png)

**Comment lire ce graphique.** PnL cumulé en millions de USD du rejeu sur EURUSD 1 minute réel (2019-2022), **net de frais** (rappelés dans le titre), pour les cinq stratégies dans le cas de base. Le panneau du bas est le drawdown (distance au dernier sommet du PnL cumulé).
Les cinq courbes sont quasi superposées et descendent régulièrement : la perte ne vient pas d'une période particulière mais de la convention de fill (voir le contrôle marche aléatoire plus bas). La zone grisée 2019-2020 est la période de sélection du tableau de bord interactif, la zone blanche 2021-2022 sa période d'évaluation : il n'existe pas de TRAIN rejoué ici, TRAIN ≤ 2018 ne sert qu'à calibrer σ.

<!-- AUTO:OVERFIT -->
<<bloc_overfit>>
<!-- /AUTO:OVERFIT -->

## Toutes les variantes

Rien n'est caché : les **30 variantes du rejeu** (5 stratégies × 3 modèles de fill × 2 conventions pour le cas « bid ET ask touchés ») sont ici, **y compris les moins mauvaises et les pires**, ainsi que les balayages Monte Carlo (sélection adverse, latence, γ, A, k). Aucune variante n'est choisie sur son résultat : la grille est fixée avant le premier rejeu.
Le même PnL quotidien de chaque variante alimente le tableau de bord interactif (identifiants identiques).

<!-- AUTO:VARIANTES -->
<<bloc_variantes>>
<!-- /AUTO:VARIANTES -->

![Toutes les variantes : PnL cumulé net des 30 rejeux, cas de base en couleur](figures/toutes_variantes.png)

**Comment lire ce graphique.** Chaque ligne grise est le PnL cumulé net d'une des 25 variantes autres que le cas de base ; les cinq lignes en couleur (quasi superposées) sont le cas de base. L'éventail des PnL cumulés finaux va de <<cumul_haut>> à <<cumul_bas>> millions de USD : la convention de fill déplace l'ampleur de la perte (le groupe le plus bas est « côté perdant seul » avec f = 1, où chaque barre qui traverse la cote est exécutée et, par construction, du côté qui perd), jamais son signe.
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
| Placebo | cotes aléatoires de même largeur moyenne que AS (<<demi_placebo>> pip de demi-spread) | δ_b, δ_a ~ U(0, 2m), indépendantes du prix et de l'inventaire |

**γ n'a pas la même unité dans AS et GLFT** (AS le multiplie par T-t, jusqu'à 32 400 s ; GLFT est stationnaire). On n'égalise donc pas γ :
on fixe un **critère d'agressivité commun, choisi a priori** (à Q/2 lots d'inventaire, la cote est décalée de 1/k pip), ce qui donne
γ_AS = <<gamma_as>> et γ_GLFT = <<gamma_glft>>. Aucun paramètre n'est optimisé sur les résultats.
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

<<table_hypotheses>>

**A, k, p, α, le spread et les frais ne sont pas mesurés** : on n'a pas de données d'ordres, seulement des barres. Ce sont des hypothèses
fixées *avant* de voir les résultats, avec une analyse de sensibilité (grille 3x3 pour A et k, balayages de p et de la latence). Les chiffres
du Monte Carlo sont donc **conditionnels** à ces hypothèses. σ = <<sigma>> pip/√s (soit <<sigma_minute>> pips par minute : une barre de
1 minute bouge d'environ 15 demi-spreads, ce qui compte pour le rejeu).

![sigma par heure](figures/sigma_par_heure.png)

**Comment lire ce graphique.** Volatilité réalisée de l'EURUSD par heure de New York, mesurée sur TRAIN 2010-2018 (variations de close entre minutes consécutives). Les barres bleues sont les heures de la session simulée (03h-12h) : c'est leur moyenne en variance qui donne σ. La volatilité monte entre 02h et 03h (ouverture de Londres) et culmine entre 08h et 09h (annonces américaines de 8h30).

## Résultats détaillés

Tous les chiffres ci-dessous sont lus dans `results/verdict_mm.json` et `results/rejeu_variantes.json` (ce fichier README est généré par `scripts/generer_readme.py`).

### Monte Carlo (<<n_sessions>> sessions de 9 h par stratégie, graines communes)

<<table_mc>>

Sharpe journalier annualisé par √252 ; IC95 par bootstrap des sessions ; CVaR 5 % = moyenne des 5 % pires journées.
Décomposition du PnL moyen (pips x lot par session) :

<<table_decomposition>>

![distributions](figures/distributions_pnl.png)

**Comment lire ce graphique.** Un histogramme par stratégie du PnL d'une session de 9 h (2 000 sessions, mêmes tirages pour toutes). Le trait noir est la moyenne, le pointillé rouge le zéro. Les moyennes sont presque égales ; ce qui change, c'est la largeur : le naïf et le placebo ont des queues de perte profondes, AS et GLFT sont resserrés autour de la moyenne.

![decomposition](figures/decomposition_pnl.png)

**Comment lire ce graphique.** Pour chaque stratégie, les composantes du PnL moyen par session (barres) et leur somme (losange noir). La capture de spread (la grande barre positive) est quasi identique partout ; la sélection adverse retire environ un cinquième ; la liquidation et les frais sont petits. Les stratégies ne diffèrent donc pas par ce qu'elles gagnent mais par le risque d'inventaire qu'elles portent.

![trajectoire](figures/trajectoire_exemple.png)

**Comment lire ce graphique.** Haut : deux minutes d'une session simulée d'AS, avec le mid, les cotes bid/ask (en escalier, car recalculées par pas de 0,1 s) et les exécutions (triangles). Milieu : l'inventaire correspondant. Bas : l'inventaire de la session entière pour les cinq stratégies, mêmes tirages ; le naïf et le placebo atteignent la borne de 20 lots (inventaire maximal moyen <<inv_naif>>), AS et surtout GLFT la contiennent bien mieux (<<inv_as>> et <<inv_glft>> lots).

À lire : la **capture de spread est à peu près la même pour tout le monde** (mêmes clients) ; ce qui change, c'est le **risque** d'inventaire.
AS et GLFT divisent l'écart-type des sessions par 3 à 5 par rapport au naïf, d'où un Sharpe de simulation bien supérieur. Le **placebo**
(cotes aléatoires de même largeur) a un Sharpe de <<sh_placebo>>, comparable au naïf (<<sh_naif>>) : le gain d'AS/GLFT vient de la
logique d'inventaire, pas de la largeur des cotes. Mais **dans un monde simulé qui obéit exactement au modèle testé, cette supériorité est
une propriété de la simulation, pas une preuve de performance**.

### Rejeu sur barres 1 minute réelles, VAL 2019-2022 (<<n_jours>> journées de Londres)

Règles (voir `mm/rejeu_reel.py`) : référence causale = close de la minute précédente (+ demi-spread de marché, HistData étant en BID) ; la
cote de la minute *i* n'utilise que des données ≤ *i*-1 (test de non-fuite : on modifie les barres futures, les cotes passées ne bougent pas) ;
le bid n'est exécuté que si la barre suivante **traverse** la cote ; si bid et ask sont tous deux atteints, on suppose l'**ordre défavorable**
(le côté qui perd passe d'abord). Trois modèles de fill : « toucher suffit », « traverser d'au moins 0,1 pip », « traverser de 0,1 pip **et**
tirer la probabilité de file f = 0,5 ». Et deux lectures du cas « bid ET ask touchés » qui encadrent la vérité : **seul le côté perdant est exécuté**
(pessimiste) ou **les deux côtés le sont** (optimiste, aller-retour à chaque barre). Cas de base : *<<modele_base_nom>>*, côté perdant seul (volontairement pessimiste : dans chaque barre où bid et ask sont atteints, le fill défavorable est le seul retenu).

**Sharpe annualisé du rejeu selon le modèle de fill** (le message central de cette section) :

<<table_fill>>

![modeles de fill](figures/rejeu_modeles_fill.png)

**Comment lire ce graphique.** Pour chaque stratégie (axe horizontal), trois barres = les trois modèles de fill (de plus en plus foncé : touche, traversée, probabiliste), avec leur IC 95 % par blocs de 10 jours. À gauche la convention « côté perdant seul », à droite « les deux côtés ». Toutes les barres sont sous zéro ; ce qui les fait varier, c'est le modèle de fill et la convention, pas la stratégie.

Trois constats.

1. **Aucune des six conventions ne donne un Sharpe positif** (de <<rj_min>> à <<rj_max>>). La simulation, elle, donnait +<<sh_naif>> à +<<sh_glft>>.
2. **Seule la probabilité de file f change vraiment le résultat.** Exiger une traversée de 0,1 pip plutôt que 0 est presque sans effet (voir la figure ci-dessous) : une barre d'une minute bouge d'environ <<sigma_minute>> pips, soit une quinzaine de demi-spreads, donc nos cotes sont
   traversées de toute façon. Plus f est grand, plus on est exécuté, donc plus on perd.
3. **Le classement en Sharpe s'inverse** : AS et GLFT font moins bien que le naïf sous les six conventions, alors qu'ils le dominaient en simulation.
   Deux effets mêlés, non démêlés : (i) quand l'espérance est négative, réduire la variance (ce que fait AS) rend le Sharpe plus négatif ; (ii) sous « deux côtés »,
   le PnL *moyen* d'AS est lui aussi plus bas. Hypothèse (non testée) pour (ii) : le décalage d'inventaire rapproche la cote du mid, donc sacrifie une partie de
   l'edge, pour un bénéfice de risque qui ne se paie pas quand chaque exécution est déjà adverse.

![sensibilité à f et au seuil](figures/rejeu_sensibilite_f_seuil.png)

**Comment lire ce graphique.** Sharpe du rejeu d'AS pour chaque couple (probabilité de file f en abscisse, traversée exigée en ordonnée, de −0,1 à +0,3 pip ; une traversée négative n'exige même pas que le mid atteigne la cote). Les cases d'une même colonne sont presque identiques : le seuil compte peu, f décide.

Le cas de base, avec **IC95 par bootstrap en blocs de 10 jours** (les PnL journaliers réels peuvent être autocorrélés ; l'IC « iid » est donné pour comparaison) :

<<table_rejeu_base>>

![PnL cumulé](figures/rejeu_val_pnl_cumule.png)

**Comment lire ce graphique.** PnL cumulé de chaque stratégie (en pips × lot, 100 USD par unité) dans le modèle de base, côté perdant seul à gauche et les deux côtés à droite ; le total final est dans la légende. Les cinq courbes sont quasi superposées et décroissent régulièrement (environ <<rj_pnl_jour>> pips x lot par jour dans le cas de base, côté perdant seul) : la perte ne vient
pas d'une période particulière mais de la convention elle-même.

**Markout** : pour chaque exécution, (mid futur - prix d'exécution) x sens, à +1, +5 et +15 minutes (pips par exécution, ± IC95 ; modèle de base,
lecture « deux côtés » pour ne pas mélanger l'artefact du choix du côté perdant) :

<<table_markout>>

![markout](figures/markout_rejeu.png)

**Comment lire ce graphique.** Markout moyen par exécution à +1, +5 et +15 minutes (une barre par stratégie), avec son IC 95 %. Une sélection adverse « réelle » donnerait un markout de plus en plus négatif avec l'horizon ; ici les trois horizons sont au même niveau : rien ne suit l'exécution.

Le markout est négatif et **constant de +1 à +15 minutes** : rien ne « suit » l'exécution, le prix ne revient pas mais ne s'éloigne pas non plus. L'edge
théorique d'une exécution (le demi-spread posé, environ 0,17 pip) est pourtant plus que mangé, et **ce n'est pas une mesure de la sélection adverse du marché
réel** : une barre qui traverse notre cote est, par construction, une barre qui bouge, et l'exécution est comptée au prix de la cote alors que le prix a déjà
dépassé la cote (traversée exigée de 0,1 pip + dépassement à l'intérieur de la barre). Contrôle : le même rejeu appliqué à <<ctl_n_jours>> journées d'une marche
aléatoire **sans dérive et sans sélection adverse**, de même sigma de minute que VAL (<<ctl_sigma>> pips), donne des résultats du même ordre de grandeur (plus négatifs côté perdant seul, quasi identiques côté deux côtés) :

<<table_controle>>

Le rejeu ne distingue donc pas l'EURUSD réel d'une marche aléatoire : son résultat mesure le coût de la **convention de fill**, pas une propriété de la microstructure réelle.
Il montre que la simulation (Sharpe positif) et le rejeu sur barres (Sharpe négatif) ne se comparent pas, pas que le marché réel punit ces stratégies.

**Placebo dans le rejeu** (<<n_graines>> graines de tirages, mêmes graines pour AS et pour le placebo ; cotes aléatoires de même largeur moyenne) :

<<table_placebo>>

![placebo](figures/placebo_rejeu.png)

**Comment lire ce graphique.** Pour chaque lecture de « bid ET ask touchés » (une colonne), le Sharpe (haut) et le PnL moyen par jour (bas) obtenus pour chacune des 30 graines de tirage, pour AS (bleu) et pour le placebo (violet). Les deux distributions se chevauchent presque en PnL moyen (aucun avantage d'AS), alors que le Sharpe d'AS est systématiquement plus négatif (moins de variance).

Dans le rejeu, **AS n'a aucun avantage d'espérance sur des cotes tirées au hasard** : PnL moyen par jour de <<pla_pnl_ref_adv>> contre <<pla_pnl_pla_adv>>
(côté perdant seul) et <<pla_pnl_ref_deux>> contre <<pla_pnl_pla_deux>> (deux côtés) ; AS ne fait mieux que le placebo dans <<pla_win_adv>> % et <<pla_win_deux>> %
des graines seulement. AS réduit bien la variance (écart-type journalier <<std_as_base>> contre <<std_pla_base>> pips x lot dans le cas de base),
mais quand l'espérance est négative, **réduire la variance dégrade le Sharpe** : c'est pourquoi AS est plus négatif que le placebo en Sharpe dans 100 % des graines.
Comparer des Sharpe sans regarder les espérances aurait donné une conclusion trompeuse. La logique d'inventaire d'AS, précieuse dans le monde simulé, ne produit
aucun gain d'espérance sur ces barres.

### Pourquoi un Sharpe de simulation n'est pas un Sharpe de marché

Trois mécanismes, absents du modèle de base, sont chacun suffisants pour détruire le Sharpe simulé.

**Sélection adverse** : p = 0 → p = 0,4 fait passer AS de <<as_p0>> à <<as_p04>>. La baisse est régulière mais modérée tant que
p·α (perte moyenne par exécution) reste sous le demi-spread.

<<table_p>>

**Latence (cotes périmées)** : le mid bouge de σ√(L·dt) entre deux mises à jour ; dès que ce mouvement dépasse le demi-spread, les cotes se font
« ramasser ». AS passe de <<as_lat_100ms>> (100 ms) à <<as_lat_1s>> à 1 s et <<as_lat_60s>> à <<lat_max_s>> s.

<<table_latence>>

![effondrement du Sharpe](figures/sharpe_effondrement.png)

**Comment lire ce graphique.** Sharpe simulé de chaque stratégie quand on augmente la part de flux informé p (à gauche) puis le délai entre deux mises à jour des cotes (à droite, échelle logarithmique). Le Sharpe baisse doucement avec p, mais passe sous zéro entre 0,5 et 1 s de latence et devient très négatif à 60 s : le rejeu sur barres 1 minute est dans cette zone.

**Le rejeu sur barres 1 minute équivaut à coter avec 60 s de latence** : la cote posée au close précédent reste fixe pendant une minute où le prix bouge de
<<sigma_minute>> pips. Le rejeu tombe dans la zone « effondrée » de la figure ci-dessus. Il ne peut donc **pas** valider un market maker à
haute fréquence ; il sert à mesurer l'écart avec la simulation et la sensibilité aux conventions de fill.

**Sensibilité aux hypothèses A, k et au gamma de la stratégie** (cases en gras = valeurs de base ; k réel ≠ k supposé par la stratégie) :

![heatmap p x k](figures/heatmap_p_k.png)

**Comment lire ce graphique.** Sharpe simulé d'AS pour chaque couple (k réel du marché en abscisse, probabilité de sélection adverse p en ordonnée) alors que la stratégie croit k = 6 ; la case en gras est le cas de base. Rouge = négatif, bleu = positif. Le Sharpe reste positif sur toute la grille (de <<pk_min>> à <<pk_max>>) : p et k seuls n'expliquent pas le rejeu.

![heatmap latence x gamma](figures/heatmap_latence_gamma.png)

**Comment lire ce graphique.** Sharpe simulé d'AS selon le gamma de la stratégie (de ×0,25 à ×4, en abscisse) et la latence (en ordonnée). À faible latence, un gamma plus grand (plus de contrôle d'inventaire) augmente le Sharpe simulé ; à partir de 1 s de latence il est négatif quel que soit gamma : on ne rattrape pas des cotes périmées en ajustant l'aversion au risque.

![heatmap A x k](figures/heatmap_A_k.png)

**Comment lire ce graphique.** Une grille 3×3 par stratégie : Sharpe simulé quand A (fréquence d'exécution) et k (sensibilité à la profondeur) réels diffèrent des croyances de la stratégie (case en gras = hypothèses de base). Les Sharpe changent d'ampleur (de <<ak_min>> à <<ak_max>> sur toute la grille et toutes les stratégies) mais restent positifs.

Ces grilles sont une **présentation de robustesse, pas une optimisation** : 3x3 pour A et k, 5x5 au plus pour les autres, et aucune valeur n'est
retenue en fonction du résultat.

## Validation et tests

<<n_tests>> tests, quelques secondes (`python -m pytest -q`) ; chaque brique est confrontée à une réponse connue.

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
> 3. Monte Carlo (<<n_sessions>> sessions, common random numbers): annualised Sharpe with bootstrap CIs; simulated Sharpe is high (AS <<sh_as>>) but collapses with adverse selection and latency.
> 4. Replayed on real EURUSD 1-minute bars (VAL 2019-2022, TEST sealed) under three fill models and two bid-and-ask conventions: Sharpe is negative everywhere (<<rj_min>> to <<rj_max>>). All 30 variants (5 strategies x 3 fill models x 2 conventions) are published, with a PSR/DSR and an interactive dashboard.
> 5. Markout at +1/+5/+15 min is negative and flat, but a driftless random-walk control reproduces it (it measures the fill convention, not real adverse selection); a block-bootstrap CI and a placebo (random quotes) show AS has no edge over chance on bars.
> 6. Take-away: a simulated Sharpe is an upper bound, not a market Sharpe. Limits: A, k, p, α are assumptions (no order data); 1-minute bars imply ~60 s quote refresh; no L2 book or queue model.
