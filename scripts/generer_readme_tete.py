"""Écrit dans README.md les blocs de chiffres, LUS dans results/*.json (aucun chiffre tapé à la main).

Quatre blocs délimités par des balises HTML (invisibles sur GitHub) sont réécrits à chaque exécution :
  <!-- AUTO:CLES -->      « Résultats clés » : trois puces, chaque chiffre avec sa réserve
  <!-- AUTO:TETE -->      frais et hypothèses (version courte), tableau de métriques simulation | rejeu réel, verdict
  <!-- AUTO:OVERFIT -->   « Overfit ou pas ? », lecture en 30 secondes
  <!-- AUTO:VARIANTES --> les 30 variantes du rejeu (repliées) et le résumé des sensibilités Monte Carlo
`scripts/generer_readme.py` appelle les mêmes fonctions pour assembler le README entier et `docs/details.md` ; un test
vérifie que les blocs sont à jour. Aucune donnée de marché requise, TEST jamais chargé.

Usage : python scripts/generer_readme_tete.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
RESULTATS = RACINE / "results"
README = RACINE / "README.md"
USD_PAR_PIP_LOT = 100.0
FILL_AFFICHE = {"touche": "touche", "traversee": "traversée", "probabiliste": "probabiliste"}
CONVENTION_AFFICHEE = {"adverse": "côté perdant seul", "deux_cotes": "les deux côtés"}
LIEN_DETAILS = "docs/details.md"


# ------------------------------------------------------------------ formats français
def fr(x, d=1):
    texte = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return texte[1:] if texte.startswith("-") and not any(c in "123456789" for c in texte) else texte  # pas de « -0 »


def ic(x, d=1):
    return f"[{fr(x[0], d)} ; {fr(x[1], d)}]"


def p3(x):
    """Probabilité : « < 0,001 » si négligeable."""
    return "< 0,001" if x < 0.001 else fr(x, 3)


def musd(pips_lot, d=1):
    """pips x lot -> millions de USD (1 pip x 1 lot = 100 USD)."""
    return fr(pips_lot * USD_PAR_PIP_LOT / 1e6, d)


def pct_ref(pips_lot, variantes, d=0):
    """pips x lot -> % du capital de référence ARBITRAIRE (100 M USD) : l'échelle à lire à côté d'un PnL en M USD."""
    return fr(pips_lot * USD_PAR_PIP_LOT / variantes["meta"]["capital_reference_usd"] * 100, d)


def musd_et_pct(pips_lot, variantes):
    return f"{musd(pips_lot)} (≈ {pct_ref(pips_lot, variantes)} %)"


def signe(x, d=1):
    return ("+" if x > 0 else "") + fr(x, d)


def tableau(entetes, lignes):
    sortie = ["| " + " | ".join(entetes) + " |", "|" + "|".join("---" for _ in entetes) + "|"]
    sortie += ["| " + " | ".join(str(c) for c in ligne) + " |" for ligne in lignes]
    return "\n".join(sortie)


def repliable(titre: str, contenu: str) -> str:
    """Bloc `<details>` (les tableaux de plus de 7 colonnes y sont repliés) ; la ligne vide après </summary> est nécessaire."""
    return f"<details>\n<summary>{titre}</summary>\n\n{contenu}\n\n</details>"


# ------------------------------------------------------------------ lecture des résultats
def charger():
    verdict = json.loads((RESULTATS / "verdict_mm.json").read_text(encoding="utf-8"))
    variantes = json.loads((RESULTATS / "rejeu_variantes.json").read_text(encoding="utf-8"))
    return verdict, variantes


def _base_par_strategie(variantes):
    """{nom de stratégie: variante du cas de base (probabiliste, côté perdant seul)}."""
    return {v["nom_strategie"]: v for v in variantes["variantes"] if v["base"]}


def _court(nom: str) -> str:
    return nom.split(" (")[0]


# ------------------------------------------------------------------ bloc CLES
def bloc_cles(verdict, variantes) -> str:
    """Trois puces : chaque chiffre est suivi de sa réserve (T2 de l'audit)."""
    mc, rj = verdict["monte_carlo"], verdict["rejeu_val"]
    sh_mc = {n: m["sharpe_annualise"] for n, m in mc.items()}
    n_bas, n_haut = min(sh_mc, key=sh_mc.get), max(sh_mc, key=sh_mc.get)
    sh_rj = [v["sharpe"] for v in variantes["variantes"]]
    base_as = _base_par_strategie(variantes)["Avellaneda-Stoikov"]
    capital = variantes["meta"]["capital_reference_usd"] / 1e6
    ctl = rj["controle_marche_aleatoire"]["resultats"]["adverse"]["Naïve symétrique"]
    lat = verdict["sensibilites_monte_carlo"]["sharpe_vs_latence"]
    i_as = lat["strategies"].index("Avellaneda-Stoikov")
    sh_lat = {ms: ligne[i_as] for ms, ligne in zip(lat["latence_ms"], lat["sharpe"])}
    return "\n".join([
        f"- **Simulation (Monte Carlo, {fr(verdict['meta']['n_sessions_monte_carlo'], 0)} sessions)** : Sharpe annualisé de **{signe(sh_mc[n_bas])}** "
        f"({_court(n_bas).lower()}) à **{signe(sh_mc[n_haut])}** ({_court(n_haut)}). *Réserve : le monde simulé obéit au modèle testé, l'espérance y est donc positive "
        "par construction (même des cotes tirées au hasard gagnent) : c'est une borne haute, pas un Sharpe de marché.*",
        f"- **Rejeu sur EURUSD 1 minute réel (VAL 2019-2022, {len(sh_rj)} variantes)** : Sharpe de **{fr(min(sh_rj))} à {fr(max(sh_rj))}** ; "
        f"cas de base d'Avellaneda-Stoikov : **{musd(base_as['pnl_cumule'])} M USD** de PnL cumulé, soit ≈ {pct_ref(base_as['pnl_cumule'], variantes)} % "
        f"d'un capital de référence arbitraire de {fr(capital, 0)} M USD (aucun PnL réel). *Réserve : une marche aléatoire sans dérive donne le même ordre de perte "
        f"(stratégie naïve, pips × lot par jour : {fr(ctl['pnl_moyen_jour_marche_aleatoire'], 0)} sur marche aléatoire, {fr(ctl['pnl_moyen_jour_reel'], 0)} sur barres réelles) : "
        "le rejeu mesure surtout la convention de remplissage (côté perdant choisi avec le close de la barre, pessimiste a posteriori), pas le marché.*",
        f"- **Ce que le projet établit** : en simulation (balayage de latence, {verdict['meta']['n_sessions_sensibilites']} sessions par cellule), le Sharpe d'Avellaneda-Stoikov passe de **{signe(sh_lat[100.0])} à 100 ms de latence à {signe(sh_lat[1000.0])} à 1 s**, "
        f"et une barre de 1 minute équivaut à 60 s de latence ({signe(sh_lat[60000.0])} dans le simulateur) : le rejeu ne contredit donc pas le simulateur, "
        "il tombe dans sa zone d'effondrement. *Réserve : A, k, p et α sont des hypothèses, pas des mesures (aucune donnée d'ordres) ; c'est une sensibilité, pas une performance.*",
    ])


# ------------------------------------------------------------------ bloc TÊTE
def frais_compacts(verdict, variantes) -> str:
    """Version courte (8 lignes) de l'encadré « frais et hypothèses » pour le premier écran du README."""
    h = verdict["hypotheses"]["hypotheses_non_mesurees"]
    rej = verdict["hypotheses"]["rejeu"]
    m = variantes["meta"]
    return "\n".join([
        "## Frais et hypothèses",
        "",
        f"- **Frais** : {fr(h['frais'], 3)} pip par exécution (≈ 0,5 USD par million : ordre de grandeur, non vérifié) + liquidation de l'inventaire résiduel en fin de session "
        f"(demi-spread de marché {fr(h['demi_spread_marche'], 2)} pip × lots détenus). Tous les PnL sont **NETS** de ces deux coûts ; 1 pip × 1 lot (1 M EUR) = {fr(m['usd_par_pip_lot'], 0)} USD.",
        f"- **Hypothèses, pas des mesures** (aucune donnée d'ordres) : A = {fr(h['A'], 2)} /s, k = {fr(h['k'], 1)} /pip, p = {fr(h['p_adverse'], 2)}, α = {fr(h['alpha'], 2)} pip. "
        f"Elles pilotent la simulation, pas le rejeu ([tableau complet]({LIEN_DETAILS}#frais-et-hypothèses)).",
        f"- **Données** : EURUSD 1 minute HistData (prix BID, heure de New York), session 03h-12h, {fr(rej['n_jours'], 0)} journées de rejeu ({m['premier_jour']} → {m['dernier_jour']}) ; non redistribuées.",
        "- **Découpage** : TRAIN ≤ 2018 (calibration de σ seulement) · VAL 2019-2022 (rejeu) · TEST 2023+ scellé, jamais lu (`PermissionError` testé).",
        "- **Latence et remplissage** : la cote de la minute *i* repose sur le close de *i*-1 (**60 s de latence implicite**) ; 3 modèles de fill × 2 lectures de « bid ET ask touchés » "
        "(cas de base : probabiliste + côté perdant seul, un choix pessimiste a posteriori : voir Limites).",
        f"- **Statistiques** : Sharpe journalier × √252 ; IC 95 % par bootstrap (blocs de {m['bloc_bootstrap_jours']} jours pour le rejeu) ; PSR et DSR sur les {m['n_essais_dsr']} variantes.",
    ])


def encadre_frais(verdict, variantes, niveau="##") -> str:
    """Encadré complet (page de détails)."""
    h = verdict["hypotheses"]["hypotheses_non_mesurees"]
    marche = verdict["hypotheses"]["marche_simule"]
    rej = verdict["hypotheses"]["rejeu"]
    fill = rej["modeles_fill (seuil_pips, f)"]
    sigma = verdict["calibration"]["sigma_session_londres_pips_par_racine_s"]
    n_jours = fr(rej["n_jours"], 0)
    m = variantes["meta"]
    return "\n".join([
        f"{niveau} Frais et hypothèses",
        "",
        "| Hypothèse | Valeur |",
        "|---|---|",
        f"| Frais par exécution | **{fr(h['frais'], 3)} pip par exécution** (≈ 0,5 USD par million : ordre de grandeur, non vérifié) + coût de liquidation de l'inventaire "
        f"résiduel en fin de session (demi-spread de marché {fr(h['demi_spread_marche'], 2)} pip × lots détenus). Tous les PnL des tableaux et des figures sont **NETS** de ces deux coûts ; "
        f"1 pip × 1 lot (1 M EUR) = {fr(m['usd_par_pip_lot'], 0)} USD |",
        f"| Spread de marché | demi-spread {fr(h['demi_spread_marche'], 2)} pip (hypothèse ; EURUSD interbancaire ≈ 0,1-0,3 pip de spread), ajouté aux prix BID de HistData pour reconstituer le mid |",
        f"| Hypothèses A, k, p, α | A = {fr(h['A'], 2)} exécution/s à profondeur 0 par côté · k = {fr(h['k'], 1)} /pip · p = {fr(h['p_adverse'], 2)} (proba de saut après exécution) · "
        f"α = {fr(h['alpha'], 2)} pip (taille du saut). **Hypothèses, pas des mesures** (aucune donnée d'ordres), fixées avant les résultats, sensibilités publiées ; elles pilotent la simulation, pas le rejeu |",
        f"| Latence | simulation : cotes recalculées toutes les {fr(marche['dt'], 1)} s (balayage jusqu'à 60 s) ; rejeu sur barres 1 minute : la cote de la minute *i* repose sur le close de *i*-1, "
        "soit **60 s de latence implicite** |",
        f"| Données | EURUSD 1 minute **HistData, prix BID, heure locale de New York** (heure d'été comprise), volume nul ; session 03h00-12h00 (= 08h-17h Londres) ; "
        f"{n_jours} journées de rejeu ({m['premier_jour']} → {m['dernier_jour']}) ; données non redistribuées (voir « Obtenir les données » dans le README) |",
        f"| Découpage | **TRAIN ≤ 2018** : calibration de σ seulement (σ = {fr(sigma, 3)} pip/√s), rien n'y est rejoué · **VAL 2019-2022** : rejeu · "
        f"**TEST 2023+ : scellé**, jamais lu (`mm/donnees.py` lève `PermissionError`, testé) |",
        f"| Conventions de fill | 3 modèles : *touche* (traversée ≥ {fr(fill['touche'][0], 1)} pip, f = {fr(fill['touche'][1], 1)}), *traversée* (≥ {fr(fill['traversee'][0], 1)} pip, f = {fr(fill['traversee'][1], 1)}), "
        f"*probabiliste* (≥ {fr(fill['probabiliste'][0], 1)} pip, file d'attente f = {fr(fill['probabiliste'][1], 1)}) × 2 lectures du cas « bid ET ask touchés » (côté perdant seul / les deux côtés). "
        "Cas de base : probabiliste + côté perdant seul |",
        "| Côté perdant seul | quand bid ET ask sont touchés dans la même barre, le côté exécuté est celui dont le **close de la barre** s'éloigne : information postérieure à la pose de la cote, "
        "retournée contre la stratégie. C'est un **choix pessimiste fait a posteriori, pas une hypothèse de fill réaliste** ; « les deux côtés » est la lecture optimiste |",
        "| Délai d'exécution | fill testé sur la barre qui SUIT la pose de la cote, jamais au prix du signal ; ordre intra-barre inconnu |",
        f"| Statistiques | Sharpe journalier × √252 ; IC 95 % par bootstrap par blocs de {m['bloc_bootstrap_jours']} jours (rejeu) ou des sessions (simulation, "
        f"{fr(verdict['meta']['n_sessions_monte_carlo'], 0)} sessions) ; PSR et DSR sur les {m['n_essais_dsr']} variantes du rejeu |",
    ])


def tableau_simulation_vs_rejeu(verdict, variantes) -> str:
    mc = verdict["monte_carlo"]
    base = _base_par_strategie(variantes)
    lignes = []
    for nom, s in mc.items():
        b = base[nom]
        lignes.append([nom, f"{fr(s['sharpe_annualise'])} {ic(s['sharpe_ic95'])}", f"{fr(b['sharpe'])} {ic(b['sharpe_ic95_blocs'])}",
                       fr(s["pnl_moyen_pips_lot"], 0), fr(b["pnl_moyen_jour"], 0), fr(s["executions_moyennes"], 0), fr(b["executions_par_jour"], 0)])
    return "\n".join([
        "## Métriques par stratégie : simulation et rejeu réel côte à côte",
        "",
        "Équivalent ici du « TRAIN | VAL » d'un projet de stratégie : à gauche le monde **simulé** (les hypothèses du modèle sont vraies par construction), "
        "à droite le **rejeu sur EURUSD réel** VAL 2019-2022 (cas de base : probabiliste, côté perdant seul). PnL en pips × lot par journée. "
        "Les deux Sharpe ne sont pas comparables (mondes différents) : on ne les divise pas.",
        "",
        tableau(["Stratégie", "Sharpe simulé [IC95]", "Sharpe rejeu VAL net [IC95]", "PnL moyen/jour simulé", "PnL moyen/jour rejeu",
                 "Exéc./jour simulé", "Exéc./jour rejeu"], lignes),
        "",
        f"*IC95 du rejeu : bootstrap par blocs de {variantes['meta']['bloc_bootstrap_jours']} jours.*",
    ])


def tableau_rejeu_detail(verdict, variantes) -> str:
    mk = verdict["rejeu_val"]["markout_par_execution_pips (modele de base)"]
    base = _base_par_strategie(variantes)
    lignes = []
    for nom, b in base.items():
        lignes.append([nom, musd_et_pct(b["pnl_cumule"], variantes), musd_et_pct(b["drawdown_max"], variantes), fr(100 * b["jours_gagnants"]) + " %",
                       fr(b["frais_par_jour"] + b["liquidation_par_jour"], 1),
                       fr(mk["adverse"][nom]["1min"]["moyenne_pips"], 2), fr(mk["deux_cotes"][nom]["1min"]["moyenne_pips"], 2),
                       p3(b["psr0"]), p3(b["dsr"])])
    capital = fr(variantes["meta"]["capital_reference_usd"] / 1e6, 0)
    return "\n".join([
        "**Rejeu VAL, cas de base : pertes, drawdown, frais payés et significativité.**",
        "",
        f"*Échelle : le « % » est le PnL en M USD rapporté à un capital de référence **arbitraire** de {capital} M USD (il ne change pas le Sharpe et ne représente aucun PnL réel).*",
        "",
        tableau(["Stratégie", "PnL cumulé 2019-2022, M USD (% du capital de réf.)", "Drawdown max, M USD (% du capital de réf.)", "Jours gagnants",
                 "Frais + liquidation payés / jour (pips × lot)", "Markout +1 min, côté perdant (pip)", "Markout +1 min, deux côtés (pip)", "PSR(0)",
                 f"DSR ({variantes['meta']['n_essais_dsr']} essais)"], lignes),
        "",
        "*Drawdown = pire baisse du PnL cumulé depuis son sommet (le PnL décroît presque en continu : drawdown ≈ perte totale). Markout = (mid futur − prix d'exécution) × sens, par exécution. "
        "Les frais et la liquidation (quelques pips × lot par jour) ne sont pas la cause de la perte : la convention de fill l'est (contrôle marche aléatoire dans les détails). "
        "PSR(0) = 0 et DSR = 0 quand tous les Sharpe sont négatifs : ces colonnes n'apportent aucune information de plus.*",
    ])


def verdict_court(verdict, variantes) -> str:
    sh = [v["sharpe"] for v in variantes["variantes"]]
    ctl = verdict["rejeu_val"]["controle_marche_aleatoire"]
    return (f"**Verdict.** Aucune des {len(sh)} variantes du rejeu n'a un Sharpe positif (de {fr(min(sh))} à {fr(max(sh))}) alors que la simulation donnait "
            f"+{fr(min(m['sharpe_annualise'] for m in verdict['monte_carlo'].values()))} à +{fr(max(m['sharpe_annualise'] for m in verdict['monte_carlo'].values()))}. "
            f"Mais le même rejeu sur {ctl['n_jours']} journées de marche aléatoire sans dérive donne un PnL du même ordre : le rejeu mesure le coût de la convention de fill sur barres de 1 minute, "
            "pas une propriété du marché réel. Le Sharpe simulé est une **borne haute**, pas un Sharpe de marché. TEST scellé.")


def bloc_tete(verdict, variantes) -> str:
    detail = repliable("Rejeu VAL, cas de base : pertes en M USD avec leur échelle, drawdown, frais, markout, PSR/DSR (9 colonnes)", tableau_rejeu_detail(verdict, variantes))
    return "\n\n".join([frais_compacts(verdict, variantes), tableau_simulation_vs_rejeu(verdict, variantes), detail, verdict_court(verdict, variantes)])


# ------------------------------------------------------------------ bloc OVERFIT
def overfit_30s(verdict, variantes) -> str:
    mc, pla = verdict["monte_carlo"], verdict["rejeu_val"]["placebo"]
    ctl = verdict["rejeu_val"]["controle_marche_aleatoire"]["resultats"]
    base = _base_par_strategie(variantes)
    n_essais = variantes["meta"]["n_essais_dsr"]
    details = ", ".join(f"{n} {fr(mc[n]['sharpe_annualise'])} → {fr(base[n]['sharpe'])}" for n in mc)
    haut = max(v["sharpe_ic95_blocs"][1] for v in variantes["variantes"])
    dsr_max = max(v["dsr"] for v in variantes["variantes"])
    psr_max = max(v["psr0"] for v in variantes["variantes"])
    nai, asr = "Naïve symétrique", "Avellaneda-Stoikov"
    return "\n".join([
        "## Overfit ou pas ? Lecture en 30 secondes",
        "",
        f"1. **Simulation contre marché réel : le Sharpe change de signe.** Sharpe simulé → Sharpe du rejeu (cas de base) : {details}. "
        f"Les {len(variantes['variantes'])} variantes du rejeu sont toutes négatives. "
        "Ce n'est pas un overfit au sens classique (rien n'a été ajusté sur la simulation : tous les paramètres sont fixés a priori) mais un écart de monde : le Sharpe simulé est une borne haute.",
        f"2. **Le placebo (cotes aléatoires) fait aussi bien qu'Avellaneda-Stoikov.** Dans le rejeu, PnL moyen par jour de {fr(pla['adverse']['pnl_moyen_jour_ref'], 0)} (AS) contre "
        f"{fr(pla['adverse']['pnl_moyen_jour_placebo'], 0)} (placebo), côté perdant seul ; AS fait mieux dans {fr(100 * pla['adverse']['part_graines_ou_ref_bat_placebo_en_pnl_moyen'], 0)} % des "
        f"{pla['graines']} graines seulement. La logique d'inventaire n'apporte aucun gain d'espérance sur ces barres.",
        f"3. **Contrôle marche aléatoire : le rejeu ne distingue pas l'EURUSD réel d'une marche sans dérive (même ordre de grandeur).** PnL moyen par jour de la stratégie naïve, côté perdant seul : "
        f"{fr(ctl['adverse'][nai]['pnl_moyen_jour_reel'], 0)} sur barres réelles contre {fr(ctl['adverse'][nai]['pnl_moyen_jour_marche_aleatoire'], 0)} sur marche aléatoire "
        f"(markout +1 min : {fr(ctl['adverse'][nai]['markout_1min_reel'], 2)} contre {fr(ctl['adverse'][nai]['markout_1min_marche_aleatoire'], 2)} pip). Le Sharpe négatif du rejeu mesure la convention de fill, pas le marché.",
        f"4. **DSR : {p3(dsr_max)} pour {n_essais} essais** (PSR(0) maximal {p3(psr_max)}) : il n'y a aucun Sharpe positif à déflater, ces deux colonnes n'apportent donc rien ici. "
        f"La borne haute de l'IC 95 % du Sharpe du rejeu la plus favorable est {fr(haut)} : zéro est exclu pour les {len(variantes['variantes'])} variantes.",
        "5. **Choisi AVANT de voir VAL : tout.** A, k, p, α, spread, frais, Q, le critère d'agressivité commun de γ (décalage de 1/k à Q/2 lots), les 3 modèles de fill, les 2 conventions et les 5 stratégies "
        "sont fixés avant le premier rejeu ; la seule grandeur calibrée est σ, sur TRAIN ≤ 2018. Aucune variante n'est retirée après coup : les 30 sont publiées. "
        "Les deux ajouts postérieurs (correction de la description du fuseau, contrôle marche aléatoire) viennent de la contre-vérification du 13/10 (réimplémentation indépendante du rejeu) et ne changent aucun chiffre existant.",
    ])


# ------------------------------------------------------------------ bloc VARIANTES
def tableau_variantes(variantes) -> str:
    lignes = []
    for v in variantes["variantes"]:
        mk = v["markout_pips"]["1min"]
        lignes.append([f"`{v['id']}`" + (" (base)" if v["base"] else ""), FILL_AFFICHE[v["modele_fill"]], CONVENTION_AFFICHEE[v["convention"]], v["strategie"],
                       f"{fr(v['sharpe'])} {ic(v['sharpe_ic95_blocs'])}", fr(v["pnl_moyen_jour"], 0), musd_et_pct(v["pnl_cumule"], variantes), fr(v["executions_par_jour"], 0),
                       fr(mk, 2), p3(v["psr0"]), p3(v["dsr"])])
    return tableau(["Variante", "Modèle de fill", "Si bid ET ask touchés", "Stratégie", "Sharpe rejeu [IC95, blocs de 10 j]", "PnL moyen/jour (pips × lot)",
                    "PnL cumulé, M USD (% du capital de réf. arbitraire de 100 M USD)", "Exécutions/jour", "Markout +1 min (pip)", "PSR(0)", "DSR"], lignes)


def resume_sensibilites(verdict) -> str:
    s = verdict["sensibilites_monte_carlo"]
    i_as = s["sharpe_vs_p_adverse"]["strategies"].index("Avellaneda-Stoikov")

    def plage(valeurs):
        return fr(min(valeurs)), fr(max(valeurs))

    p, lat = s["sharpe_vs_p_adverse"], s["sharpe_vs_latence"]
    g = s["sharpe_AS_latence_x_gamma"]
    ak = s["sharpe_A_x_k_reels"]
    pk = s["sharpe_AS_p_adverse_x_k_reel"]
    gammas = g["gamma"]
    lignes = [
        ["sélection adverse p", f"{fr(p['p'][0], 1)} → {fr(p['p'][-1], 1)}", *plage([r[i_as] for r in p["sharpe"]])],
        ["latence (délai entre deux mises à jour des cotes)", f"{fr(lat['latence_ms'][0], 0)} ms → {fr(lat['latence_ms'][-1] / 1000, 0)} s", *plage([r[i_as] for r in lat["sharpe"]])],
        ["γ de la stratégie, à latence 100 ms", f"× {fr(gammas[0] / gammas[2], 2)} → × {fr(gammas[-1] / gammas[2], 0)} autour de la base", *plage(g["sharpe"][0])],
        ["A et k réels du marché (la stratégie garde ses croyances)", f"A de {fr(ak['A'][0], 2)} à {fr(ak['A'][-1], 2)}, k de {fr(ak['k'][0], 1)} à {fr(ak['k'][-1], 1)}",
         *plage([x[i_as] for ligne in ak["sharpe"] for x in ligne])],
        ["p et k réel", f"p de {fr(pk['p'][0], 1)} à {fr(pk['p'][-1], 1)}, k de {fr(pk['k'][0], 0)} à {fr(pk['k'][-1], 0)}", *plage([x for ligne in pk["sharpe"] for x in ligne])],
    ]
    return "\n".join([
        f"**Sensibilités Monte Carlo** ({verdict['meta']['n_sessions_sensibilites']} sessions par cellule, tirages communs ; Sharpe simulé d'Avellaneda-Stoikov ; "
        f"tableaux complets et figures dans [les détails]({LIEN_DETAILS}#pourquoi-un-sharpe-de-simulation-nest-pas-un-sharpe-de-marché)) :",
        "",
        tableau(["Paramètre balayé", "Plage", "Sharpe AS le plus bas", "Sharpe AS le plus haut"], lignes),
    ])


def bloc_variantes(verdict, variantes) -> str:
    return "\n\n".join([repliable("Tableau des 30 variantes (11 colonnes)", tableau_variantes(variantes)), resume_sensibilites(verdict)])


# ------------------------------------------------------------------ injection
def injecter(texte: str, nom: str, contenu: str) -> str:
    motif = re.compile(rf"(<!-- AUTO:{nom} -->)(.*?)(<!-- /AUTO:{nom} -->)", re.S)
    if not motif.search(texte):
        raise SystemExit(f"balises AUTO:{nom} introuvables dans README.md")
    return motif.sub(lambda m: f"{m.group(1)}\n{contenu}\n{m.group(3)}", texte)


def blocs(verdict, variantes) -> dict:
    return {"CLES": bloc_cles(verdict, variantes), "TETE": bloc_tete(verdict, variantes), "OVERFIT": overfit_30s(verdict, variantes),
            "VARIANTES": bloc_variantes(verdict, variantes)}


def main() -> None:
    verdict, variantes = charger()
    brut = README.read_bytes()
    crlf = brut.count(b"\r\n") > brut.count(b"\n") / 2
    texte = brut.decode("utf-8").replace("\r\n", "\n")
    for nom, contenu in blocs(verdict, variantes).items():
        texte = injecter(texte, nom, contenu)
    README.write_bytes((texte.replace("\n", "\r\n") if crlf else texte).encode("utf-8"))
    print("README.md : blocs AUTO:CLES, AUTO:TETE, AUTO:OVERFIT, AUTO:VARIANTES réécrits depuis results/")


if __name__ == "__main__":
    main()
