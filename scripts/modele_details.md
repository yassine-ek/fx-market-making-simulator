<!-- Fichier généré par scripts/generer_readme.py à partir de scripts/modele_details.md : éditer le modèle, pas ce fichier. -->
# Détails : méthode, résultats, validation

Page générée par `scripts/generer_readme.py` : tous les chiffres sont lus dans `results/verdict_mm.json` et `results/rejeu_variantes.json`. Retour au [README](../README.md).

Sommaire : [frais et hypothèses](#frais-et-hypothèses) · [méthode](#méthode) · [résultats détaillés](#résultats-détaillés) · [pourquoi un Sharpe de simulation n'est pas un Sharpe de marché](#pourquoi-un-sharpe-de-simulation-nest-pas-un-sharpe-de-marché) · [validation et tests](#validation-et-tests) · [positionnement](#positionnement-face-aux-dépôts-github) · [English summary](#english-summary)

<<bloc_frais_complets>>

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

**γ est l'aversion au risque (CARA) dans AS comme dans GLFT : même grandeur, mêmes unités.** Ce qui diffère, c'est l'effet d'un même γ. Dans AS, le décalage
des cotes contre l'inventaire vaut q·γ·σ²·(T-t) : il croît avec l'horizon restant, jusqu'à 32 400 s. Dans GLFT (stationnaire, horizon long), la pente du
décalage est c2, qui croît en √γ. À γ égal, les deux stratégies ne sont donc pas également agressives, et comparer à γ égal n'aurait pas de sens. On n'égalise pas γ mais le
**skew** : un **critère d'agressivité commun, choisi a priori** (à Q/2 lots d'inventaire, la cote est décalée de 1/k pip ; pour AS, décalage moyen de la session, T-t = T/2 ;
pour GLFT, pente c2 × Q/2). Cela donne γ_AS = <<gamma_as>> et γ_GLFT = <<gamma_glft>>, un rapport d'environ <<ratio_gamma>> qui vient de cette différence d'échelle effective
et non d'un changement d'unité. Aucun paramètre n'est optimisé sur les résultats.
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
du Monte Carlo sont donc **conditionnels** à ces hypothèses.

**Deux σ de minute, deux périodes.** σ = <<sigma>> pip/√s est mesuré sur TRAIN 2010-2018 (variations de close entre minutes consécutives, moyenne en variance sur les heures 03h-12h),
soit <<sigma_minute>> pips par minute : c'est le σ du Monte Carlo. La volatilité de minute mesurée sur les barres du rejeu VAL 2019-2022 (écart-type des variations de close d'une barre à la suivante dans la session ;
c'est aussi le σ du contrôle marche aléatoire) est de <<ctl_sigma>> pips, soit <<ratio_sigma>> fois moins : VAL est moins volatil que TRAIN. Les deux estimateurs sont voisins mais pas identiques
(les minutes manquantes sont ignorées pour TRAIN et remplies par la barre précédente pour VAL), l'écart n'est donc pas purement un changement de régime.
On n'harmonise pas : recalibrer σ sur VAL reviendrait à ajuster la simulation sur la période d'évaluation du rejeu, et le Sharpe simulé et celui du rejeu ne sont de toute façon pas comparables.
Pour lire le rejeu, c'est le σ de VAL qui compte : une barre de VAL bouge d'environ <<ctl_sigma>> pips, soit <<demis_val>> demi-spreads de <<demi_placebo>> pip (<<demis_train>> avec le σ de TRAIN) ;
dans les deux cas bien plus que le demi-spread posé, donc les cotes sont traversées.

![sigma par heure](../figures/sigma_par_heure.png)

**Comment lire ce graphique.** Volatilité réalisée de l'EURUSD par heure de New York, mesurée sur TRAIN 2010-2018 (variations de close entre minutes consécutives). Les barres bleues sont les heures de la session simulée (03h-12h) : c'est leur moyenne en variance qui donne σ. La volatilité monte entre 02h et 03h (ouverture de Londres) et culmine entre 08h et 09h (annonces américaines de 8h30).

## Résultats détaillés

Tous les chiffres ci-dessous sont lus dans `results/verdict_mm.json` et `results/rejeu_variantes.json` (cette page est générée par `scripts/generer_readme.py`).

### Monte Carlo (<<n_sessions>> sessions de 9 h par stratégie, graines communes)

<<table_mc>>

Sharpe journalier annualisé par √252 ; IC95 par bootstrap des sessions ; CVaR 5 % = moyenne des 5 % pires journées.
Décomposition du PnL moyen (pips x lot par session) :

<<table_decomposition>>

![distributions](../figures/distributions_pnl.png)

**Comment lire ce graphique.** Un histogramme par stratégie du PnL d'une session de 9 h (2 000 sessions, mêmes tirages pour toutes). Le trait noir est la moyenne, le pointillé rouge le zéro. Les moyennes sont presque égales ; ce qui change, c'est la largeur : le naïf et le placebo ont des queues de perte profondes, AS et GLFT sont resserrés autour de la moyenne.

![decomposition](../figures/decomposition_pnl.png)

**Comment lire ce graphique.** Pour chaque stratégie, les composantes du PnL moyen par session (barres) et leur somme (losange noir). La capture de spread (la grande barre positive) est quasi identique partout ; la sélection adverse retire environ un cinquième ; la liquidation et les frais sont petits. Les stratégies ne diffèrent donc pas par ce qu'elles gagnent mais par le risque d'inventaire qu'elles portent.

![trajectoire](../figures/trajectoire_exemple.png)

**Comment lire ce graphique.** Haut : deux minutes d'une session simulée d'AS, avec le mid, les cotes bid/ask (en escalier, car recalculées par pas de 0,1 s) et les exécutions (triangles). Milieu : l'inventaire correspondant. Bas : l'inventaire de la session entière pour les cinq stratégies, mêmes tirages ; le naïf et le placebo atteignent la borne de 20 lots (inventaire maximal moyen <<inv_naif>>), AS et surtout GLFT la contiennent bien mieux (<<inv_as>> et <<inv_glft>> lots).

À lire : la **capture de spread est à peu près la même pour tout le monde** (mêmes clients) ; ce qui change, c'est le **risque** d'inventaire.
AS et GLFT divisent l'écart-type des sessions par 3 à 5 par rapport au naïf, d'où un Sharpe de simulation bien supérieur. Le **placebo**
(cotes aléatoires de même largeur) a un Sharpe de <<sh_placebo>>, comparable au naïf (<<sh_naif>>) : le gain d'AS/GLFT vient de la
logique d'inventaire, pas de la largeur des cotes. Mais **dans un monde simulé qui obéit exactement au modèle testé, cette supériorité est
une propriété de la simulation, pas une preuve de performance**.

### Rejeu sur barres 1 minute réelles, VAL 2019-2022 (<<n_jours>> journées de Londres)

Règles (voir `mm/rejeu_reel.py`) : référence causale = close de la minute précédente (+ demi-spread de marché, HistData étant en BID) ; la
cote de la minute *i* n'utilise que des données ≤ *i*-1 (test de non-fuite : on modifie les barres futures, les cotes passées ne bougent pas) ;
le bid n'est exécuté que si la barre suivante **traverse** la cote. Trois modèles de fill : « toucher suffit », « traverser d'au moins 0,1 pip », « traverser de 0,1 pip **et**
tirer la probabilité de file f = 0,5 ».

**Si bid et ask sont tous deux atteints dans la même barre**, l'ordre intra-barre est inconnu. Deux lectures encadrent la vérité : **« côté perdant seul »** (seul le côté perdant est exécuté, lecture pessimiste)
ou **« les deux côtés »** (aller-retour à chaque barre, lecture optimiste). Le côté « perdant » est celui dont le **close de la barre** s'éloigne de la cote (`C - bid <= ask - C` dans `mm/rejeu_reel.py`) :
ce critère utilise une information postérieure à la pose des cotes, retournée contre la stratégie. C'est donc un **choix pessimiste fait a posteriori (un oracle adverse), pas une hypothèse de remplissage réaliste** :
le « cas de base » (probabiliste + côté perdant seul) est une borne basse volontairement punitive, qui n'estime pas le PnL d'un vrai market maker. Une lecture non biaisée demanderait des ticks bid/ask
ou un carnet L2 avec la position dans la file.

**Sharpe annualisé du rejeu selon le modèle de fill** (le message central de cette section) :

<<table_fill>>

![modeles de fill](../figures/rejeu_modeles_fill.png)

**Comment lire ce graphique.** Pour chaque stratégie (axe horizontal), trois barres = les trois modèles de fill (de plus en plus foncé : touche, traversée, probabiliste), avec leur IC 95 % par blocs de 10 jours. À gauche la convention « côté perdant seul », à droite « les deux côtés ». Toutes les barres sont sous zéro ; ce qui les fait varier, c'est le modèle de fill et la convention, pas la stratégie.

Trois constats.

1. **Aucune des six conventions ne donne un Sharpe positif** (de <<rj_min>> à <<rj_max>>). La simulation, elle, donnait +<<sh_naif>> à +<<sh_glft>>.
2. **Seule la probabilité de file f change vraiment le résultat.** Exiger une traversée de 0,1 pip plutôt que 0 est presque sans effet (voir la figure ci-dessous) : une barre d'une minute bouge d'environ <<ctl_sigma>> pips en VAL (<<sigma_minute>> avec le σ de TRAIN du simulateur), soit <<demis_val>> à <<demis_train>> demi-spreads, donc nos cotes sont
   traversées de toute façon. Plus f est grand, plus on est exécuté, donc plus on perd.
3. **Le classement en Sharpe s'inverse** : AS et GLFT font moins bien que le naïf sous les six conventions, alors qu'ils le dominaient en simulation.
   Deux effets mêlés, non démêlés : (i) quand l'espérance est négative, réduire la variance (ce que fait AS) rend le Sharpe plus négatif ; (ii) sous « deux côtés »,
   le PnL *moyen* d'AS est lui aussi plus bas. Hypothèse (non testée) pour (ii) : le décalage d'inventaire rapproche la cote du mid, donc sacrifie une partie de
   l'edge, pour un bénéfice de risque qui ne se paie pas quand chaque exécution est déjà adverse.

![sensibilité à f et au seuil](../figures/rejeu_sensibilite_f_seuil.png)

**Comment lire ce graphique.** Sharpe du rejeu d'AS pour chaque couple (probabilité de file f en abscisse, traversée exigée en ordonnée, de −0,1 à +0,3 pip ; une traversée négative n'exige même pas que le mid atteigne la cote). Les cases d'une même colonne sont presque identiques : le seuil compte peu, f décide.

Le cas de base, avec **IC95 par bootstrap en blocs de 10 jours** (les PnL journaliers réels peuvent être autocorrélés ; l'IC « iid » est donné pour comparaison) :

<<table_rejeu_base>>

![PnL cumulé](../figures/rejeu_val_pnl_cumule.png)

**Comment lire ce graphique.** PnL cumulé de chaque stratégie (en pips × lot, 100 USD par unité) dans le modèle de base, côté perdant seul à gauche et les deux côtés à droite ; le total final est dans la légende. Les cinq courbes sont quasi superposées et décroissent régulièrement (environ <<rj_pnl_jour>> pips x lot par jour dans le cas de base, côté perdant seul) : la perte ne vient
pas d'une période particulière mais de la convention elle-même. Pour l'échelle : les PnL en M USD des autres figures et du tableau de bord sont rapportés à un capital de référence arbitraire de <<capital_ref>> M USD (1 M USD = 1 %).

**Markout** : pour chaque exécution, (mid futur - prix d'exécution) x sens, à +1, +5 et +15 minutes (pips par exécution, ± IC95 ; modèle de base,
lecture « deux côtés » pour ne pas mélanger l'artefact du choix du côté perdant) :

<<table_markout>>

![markout](../figures/markout_rejeu.png)

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

![placebo](../figures/placebo_rejeu.png)

**Comment lire ce graphique.** Pour chaque lecture de « bid ET ask touchés » (une colonne), le Sharpe (haut) et le PnL moyen par jour (bas) obtenus pour chacune des 30 graines de tirage, pour AS (bleu) et pour le placebo (violet). Les deux distributions se chevauchent presque en PnL moyen (aucun avantage d'AS), alors que le Sharpe d'AS est systématiquement plus négatif (moins de variance).

Dans le rejeu, **AS n'a aucun avantage d'espérance sur des cotes tirées au hasard** : PnL moyen par jour de <<pla_pnl_ref_adv>> contre <<pla_pnl_pla_adv>>
(côté perdant seul) et <<pla_pnl_ref_deux>> contre <<pla_pnl_pla_deux>> (deux côtés) ; AS ne fait mieux que le placebo dans <<pla_win_adv>> % et <<pla_win_deux>> %
des graines seulement. AS réduit bien la variance (écart-type journalier <<std_as_base>> contre <<std_pla_base>> pips x lot dans le cas de base),
mais quand l'espérance est négative, **réduire la variance dégrade le Sharpe** : c'est pourquoi AS est plus négatif que le placebo en Sharpe dans 100 % des graines.
Comparer des Sharpe sans regarder les espérances aurait donné une conclusion trompeuse. La logique d'inventaire d'AS, précieuse dans le monde simulé, ne produit
aucun gain d'espérance sur ces barres.

## Pourquoi un Sharpe de simulation n'est pas un Sharpe de marché

Trois mécanismes, absents du modèle de base, sont chacun suffisants pour détruire le Sharpe simulé.

**Sélection adverse** : p = 0 → p = 0,4 fait passer AS de <<as_p0>> à <<as_p04>>. La baisse est régulière mais modérée tant que
p·α (perte moyenne par exécution) reste sous le demi-spread.

<<table_p>>

*Ce tableau vient de <<n_sessions_mc_sens>> sessions par cellule (graine 777) ; le tableau principal du Monte Carlo en a <<n_sessions>> (graine 20260713). À p = 0,2, AS vaut <<sh_as>> dans le second et <<as_p02_sens>> ici, GLFT <<sh_glft>> contre <<glft_p02_sens>> : deux jeux de tirages, écart compris dans les IC.*

**Latence (cotes périmées)** : le mid bouge de σ√(L·dt) entre deux mises à jour ; dès que ce mouvement dépasse le demi-spread, les cotes se font
« ramasser ». AS passe de <<as_lat_100ms>> (100 ms) à <<as_lat_1s>> à 1 s et <<as_lat_60s>> à <<lat_max_s>> s.

<<table_latence>>

![effondrement du Sharpe](../figures/sharpe_effondrement.png)

**Comment lire ce graphique.** Sharpe simulé de chaque stratégie quand on augmente la part de flux informé p (à gauche) puis le délai entre deux mises à jour des cotes (à droite, échelle logarithmique). Le Sharpe baisse doucement avec p, mais passe sous zéro entre 0,5 et 1 s de latence et devient très négatif à 60 s : le rejeu sur barres 1 minute est dans cette zone.

**Le rejeu sur barres 1 minute équivaut à coter avec 60 s de latence** : la cote posée au close précédent reste fixe pendant une minute où le prix bouge de
<<ctl_sigma>> pips en VAL (<<sigma_minute>> avec le σ de TRAIN). Le rejeu tombe dans la zone « effondrée » de la figure ci-dessus : le simulateur prédit lui-même un Sharpe très négatif à 60 s,
donc le rejeu ne le contredit pas, il le confirme. Il ne peut donc **pas** valider un market maker à
haute fréquence ; il sert à mesurer l'écart avec la simulation et la sensibilité aux conventions de fill.

**Sensibilité aux hypothèses A, k et au gamma de la stratégie** (cases en gras = valeurs de base ; k réel ≠ k supposé par la stratégie) :

![heatmap p x k](../figures/heatmap_p_k.png)

**Comment lire ce graphique.** Sharpe simulé d'AS pour chaque couple (k réel du marché en abscisse, probabilité de sélection adverse p en ordonnée) alors que la stratégie croit k = 6 ; la case en gras est le cas de base. Rouge = négatif, bleu = positif. Le Sharpe reste positif sur toute la grille (de <<pk_min>> à <<pk_max>>) : p et k seuls n'expliquent pas le rejeu.

![heatmap latence x gamma](../figures/heatmap_latence_gamma.png)

**Comment lire ce graphique.** Sharpe simulé d'AS selon le gamma de la stratégie (de ×0,25 à ×4, en abscisse) et la latence (en ordonnée). À faible latence, un gamma plus grand (plus de contrôle d'inventaire) augmente le Sharpe simulé ; à partir de 1 s de latence il est négatif quel que soit gamma : on ne rattrape pas des cotes périmées en ajustant l'aversion au risque.

![heatmap A x k](../figures/heatmap_A_k.png)

**Comment lire ce graphique.** Une grille 3×3 par stratégie : Sharpe simulé quand A (fréquence d'exécution) et k (sensibilité à la profondeur) réels diffèrent des croyances de la stratégie (case en gras = hypothèses de base). Les Sharpe changent d'ampleur (de <<ak_min>> à <<ak_max>> sur toute la grille et toutes les stratégies) mais restent positifs.

Ces grilles sont une **présentation de robustesse, pas une optimisation** : 3x3 pour A et k, 5x5 au plus pour les autres, et aucune valeur n'est
retenue en fonction du résultat.

## Validation et tests

<<n_tests>> tests collectés, quelques secondes (`python -m pytest -q`) ; certains lisent les données de marché locales et sont sautés sans elles. Chaque brique est confrontée à une réponse connue.

- **Comptabilité** : le PnL obtenu autrement (`cash + inventaire x mid - liquidation`) coïncide avec la somme des composantes à 1e-9, en simulation et dans le rejeu, pour toutes les stratégies et conventions.
- **Cas limites exacts** : avec σ = 0 et p = 0, le PnL est exactement (demi-spread posé) × (nombre d'exécutions) moins la liquidation ; l'inventaire ne dépasse jamais la borne Q ; mêmes graines = mêmes résultats, graines différentes = résultats différents.
- **Non-fuite** : modifier les barres futures ne change aucune cote passée du rejeu ; le TEST 2023+ lève `PermissionError` à la lecture.
- **Formules** : AS, GLFT, prix de réservation et constantes c1, c2 contre leurs expressions fermées ; σ retrouvé à quelques pour cent sur des barres synthétiques, sans fabriquer de volatilité avec les trous.
- **Rejeu** : fills (traversée de 0,1 pip, probabilité de file, ordre défavorable) vérifiés sur des barres écrites à la main ; markout recalculé à la main ; contrôle marche aléatoire (le markout négatif y apparaît déjà) ; fuseau (réouverture hebdomadaire à 17h00 en juillet comme en janvier, sur les données réelles).
- **Significativité** : PSR et DSR contre des valeurs connues (Sharpe nul, grand échantillon, nombre d'essais croissant).
- **Cohérence des sorties** : le PnL quotidien exporté redonne exactement le Sharpe de `results/verdict_mm.json` pour les 30 variantes ; `docs/data.json` est cohérent avec `results/` et ne contient aucune date ≥ 2023 ; les blocs de chiffres du README et cette page sont à jour ; le nombre de tests annoncé est exact ; les tableaux de plus de 7 colonnes du README sont repliés ; aucun lien de tableau de bord inexistant ; aucun chemin absolu de machine dans le dépôt (le dossier `.venv` éventuel est ignoré).
- **Données absentes** : sans les données HistData, les scripts de calcul s'arrêtent avec un message qui indique où les télécharger et l'arborescence attendue, sans trace d'erreur brute.
- **Contre-vérification du 13/10** par réimplémentation indépendante du rejeu : réimplémentation Python pure (mêmes exécutions et mêmes PnL en mode « deux côtés », à 4e-10), contrôle marche aléatoire ajouté après avoir montré que le markout négatif n'était pas une mesure de la sélection adverse, description du fuseau corrigée (aucun chiffre existant n'a changé).

## Positionnement face aux dépôts GitHub

D'après une recherche du 13/10/2026 (71 dépôts de market making, microstructure et exécution ; README lus, code non exécuté) :

| Dépôt | Ce que c'est | Ce que ce projet apporte en plus |
|---|---|---|
| [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) | backtester Rust/Numba sur carnet L2/L3 avec latence de flux, latence d'ordre et file d'attente | FX sur barres 1 min, markout, placebo, IC par blocs ; *eux* modélisent la file et la latence, *moi* je les traite en sensibilité |
| [JJJerome/mbt_gym](https://github.com/JJJerome/mbt_gym) | environnements gym vectorisés AS / Cartea-Jaimungal / exécution, avec solutions analytiques | calibration de σ sur données réelles, rejeu hors échantillon, split temporel strict |
| [cuemacro/tcapy](https://github.com/cuemacro/tcapy) | TCA FX spot (slippage, markout, benchmarks) | markout intégré à un simulateur de cotation (tcapy mesure, ne cote pas) |
| [nautechsystems/nautilus_trader](https://github.com/nautechsystems/nautilus_trader) | moteur événementiel de production, même code backtest/live, modèles de fill et de latence | périmètre volontairement réduit : le sujet ici est la validité du Sharpe, pas l'infrastructure |
| [abides-sim/abides](https://github.com/abides-sim/abides) | simulation multi-agents avec latences réseau | flux de fond synthétique remplacé par un modèle de flux informé à 2 paramètres (p, α) et des barres réelles |
| [fedecaccia/avellaneda-stoikov](https://github.com/fedecaccia/avellaneda-stoikov) | implémentation Python simple d'AS, fills de Poisson et paramètres (γ, σ, k) posés à la main, prix simulé | comparaison à GLFT, naïf et placebo ; sélection adverse et latence ; critère d'agressivité commun plutôt qu'un γ posé à la main (A et k sont aussi des hypothèses ici, mais avec grille de sensibilité) |
| [hummingbot/hummingbot](https://github.com/hummingbot/hummingbot) | framework de bots (pure MM, AS), orienté exploitation crypto, peu de mesure d'adverse selection d'après son README | markout par exécution et placebo ; pas de connecteurs ni de live |
| [DrAshBooth/PyLOB](https://github.com/DrAshBooth/PyLOB) | carnet d'ordres Python, hypothèse de latence nulle annoncée dans son README | latence et cotes périmées explicites |

Lacunes récurrentes relevées dans ces dépôts, que ce projet traite : latence et file d'attente absentes ou posées à la main ; fills « de Poisson » sans exiger que le
prix traverse la cote ; **pas de markout** (un seul dépôt sur la vingtaine de market making examinés l'annonce) ; pas de split TRAIN/VAL/TEST ni de validation sur données
réelles ; **pas d'IC ni de placebo**. Le FX est quasi absent de cet écosystème (le seul dépôt explicitement « FX market making » repéré a un README d'une ligne).
Ce que ce projet **n'a pas** : carnet L2, modèle de file d'attente, apprentissage par renforcement, code live, multi-actifs.

## English summary

> 1. FX market-making simulator (numba core, seeded `default_rng` draws): naive quotes, Avellaneda-Stoikov (2008), capped-skew AS, GLFT (2013), random-quote placebo.
> 2. Poisson fills A·exp(-k·δ), adverse-selection jumps, stale-quote latency; PnL split into spread capture / inventory / liquidation / fees, identity tested to 1e-9.
> 3. Monte Carlo (<<n_sessions>> sessions, common random numbers): annualised Sharpe with bootstrap CIs; simulated Sharpe is high (AS <<sh_as>>) but collapses with adverse selection and latency.
> 4. Replayed on real EURUSD 1-minute bars (VAL 2019-2022, TEST sealed) under three fill models and two bid-and-ask conventions: Sharpe is negative everywhere (<<rj_min>> to <<rj_max>>). All 30 variants (5 strategies x 3 fill models x 2 conventions) are published, with a PSR/DSR and an interactive dashboard.
> 5. Markout at +1/+5/+15 min is negative and flat, but a driftless random-walk control reproduces it (it measures the fill convention, not real adverse selection); a block-bootstrap CI and a placebo (random quotes) show AS has no edge over chance on bars.
> 6. Take-away: a simulated Sharpe is an upper bound, not a market Sharpe. The "loser side" convention uses the bar's close, a pessimistic choice made after the fact, not a realistic fill. Limits: A, k, p, α are assumptions (no order data); 1-minute bars imply ~60 s quote refresh; no L2 book or queue model.
