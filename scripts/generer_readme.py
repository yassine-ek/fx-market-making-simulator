"""Assemble README.md à partir de scripts/modele_readme.md et de results/*.json.

Chaque `<<cle>>` du modèle est remplacé par un chiffre ou un tableau lu dans les résultats : le README ne peut pas
contredire les résultats (relancer ce script après run_all.py ou exporter_pnl_rejeu.py). Décimales à la française.
Les blocs de tête (frais, métriques, « overfit ou pas ? », 30 variantes) viennent de `generer_readme_tete.py`.

Usage : python scripts/generer_readme.py
"""
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import generer_readme_tete as tete  # noqa: E402
from generer_readme_tete import fr, ic, tableau  # noqa: E402

N_TESTS = 63  # nombre de tests de la suite complète (badge et section « Validation et tests ») : à mettre à jour avec pytest


def construire() -> str:
    """Texte complet du README (rien n'est écrit sur le disque)."""
    v, variantes = tete.charger()
    mc, rj = v["monte_carlo"], v["rejeu_val"]
    noms = list(mc)
    court = {n: n.replace(" (cotes aléatoires)", "").replace(" asymptotique", "").replace(" symétrique", "") for n in noms}
    sens = v["sensibilites_monte_carlo"]
    hyp = v["hypotheses"]["hypotheses_non_mesurees"]
    marche = v["hypotheses"]["marche_simule"]
    strat = v["hypotheses"]["strategies"]
    base_rejeu = rj["base"]
    modeles = rj["par_modele_de_fill"]
    modele_base = rj["modele_de_base"]
    placebo = rj["placebo"]
    mk = rj["markout_par_execution_pips (modele de base)"]
    seuil_f = v["hypotheses"]["rejeu"]["modeles_fill (seuil_pips, f)"]
    ctl = rj["controle_marche_aleatoire"]
    cumuls = [x["pnl_cumule"] for x in variantes["variantes"]]
    ak = [x for ligne in sens["sharpe_A_x_k_reels"]["sharpe"] for cellule in ligne for x in cellule]
    pk = [x for ligne in sens["sharpe_AS_p_adverse_x_k_reel"]["sharpe"] for x in ligne]

    valeurs = {
        "bloc_tete": tete.bloc_tete(v, variantes),
        "bloc_overfit": tete.overfit_30s(v, variantes),
        "bloc_variantes": tete.bloc_variantes(v, variantes),
        "n_tests": str(N_TESTS),
        "sigma": fr(v["calibration"]["sigma_session_londres_pips_par_racine_s"], 3),
        "sigma_minute": fr(v["calibration"]["sigma_session_londres_pips_par_racine_s"] * 60 ** 0.5, 2),
        "n_sessions": f"{v['meta']['n_sessions_monte_carlo']:,}".replace(",", " "),
        "n_sessions_sens": str(v["meta"]["n_sessions_sensibilites"]),
        "n_jours": str(v["hypotheses"]["rejeu"]["n_jours"]),
        "demi_placebo": fr(v["hypotheses"]["placebo_demi_spread_moyen_pips"], 3),
        "gamma_as": f"{strat[noms[1]]['gamma']:.2e}".replace(".", ","),
        "gamma_glft": f"{strat[noms[3]]['gamma']:.2e}".replace(".", ","),
        "table_mc": tableau(
            ["Stratégie", "Sharpe annualisé", "IC95 bootstrap", "PnL moyen (pips x lot)", "écart-type", "P(perte)",
             "CVaR 5 %", "inventaire max (moy. / p95)", "exécutions"],
            [[n, fr(mc[n]["sharpe_annualise"]), ic(mc[n]["sharpe_ic95"]), fr(mc[n]["pnl_moyen_pips_lot"], 0),
              fr(mc[n]["pnl_ecart_type"], 0), fr(100 * mc[n]["proba_perte"]) + " %", fr(mc[n]["cvar_5pct"], 0),
              f"{fr(mc[n]['inventaire_max_moyen'])} / {fr(mc[n]['inventaire_max_p95'], 0)}",
              fr(mc[n]["executions_moyennes"], 0)] for n in noms]),
        "table_decomposition": tableau(
            ["Stratégie", "capture de spread", "inventaire : diffusion", "inventaire : sélection adverse", "liquidation",
             "frais", "= PnL moyen"],
            [[n, fr(d["capture_spread"], 0), fr(d["inventaire_total"] - d["dont_selection_adverse"], 0),
              fr(d["dont_selection_adverse"], 0), fr(d["cout_liquidation"], 1), fr(d["frais"], 0),
              fr(mc[n]["pnl_moyen_pips_lot"], 0)] for n in noms for d in [mc[n]["decomposition_moyenne"]]]),
        "table_p": tableau(
            ["p (sélection adverse)"] + [court[n] for n in noms],
            [[fr(p, 2)] + [fr(x) for x in lig] for p, lig in zip(sens["sharpe_vs_p_adverse"]["p"], sens["sharpe_vs_p_adverse"]["sharpe"])]),
        "table_latence": tableau(
            ["délai entre deux mises à jour des cotes"] + [court[n] for n in noms],
            [[f"{fr(ms, 0)} ms" if ms < 1000 else f"{fr(ms / 1000, 0)} s"] + [fr(x) for x in lig]
             for ms, lig in zip(sens["sharpe_vs_latence"]["latence_ms"], sens["sharpe_vs_latence"]["sharpe"])]),
        "table_fill": tableau(
            ["modèle de fill (traversée, f)", "bid ET ask touchés"] + [court[n] for n in noms],
            [[f"{m} ({fr(seuil_f[m][0], 1)} pip, f = {fr(seuil_f[m][1], 2)})", "seul le côté perdant (pessimiste)" if r == "adverse" else "les deux côtés (optimiste)"]
             + [fr(modeles[m][r][n]["sharpe_annualise"]) for n in noms]
             for m in modeles for r in ("adverse", "deux_cotes")]),
        "table_rejeu_base": tableau(
            ["Stratégie", "Sharpe", "IC95 par blocs de 10 j", "IC95 iid (trop étroit)", "PnL moyen / jour", "exécutions / jour", "inventaire max moyen"],
            [[n, fr(base_rejeu[n]["sharpe_annualise"]), ic(base_rejeu[n]["sharpe_ic95"]), ic(base_rejeu[n]["sharpe_ic95_iid"]),
              fr(base_rejeu[n]["pnl_moyen_pips_lot"], 0), fr(base_rejeu[n]["executions_moyennes"], 0),
              fr(base_rejeu[n]["inventaire_max_moyen"])] for n in noms]),
        "table_markout": tableau(
            ["Stratégie", "+1 min", "+5 min", "+15 min"],
            [[n] + [f"{fr(mk['deux_cotes'][n][h]['moyenne_pips'], 2)} ± {fr(1.96 * mk['deux_cotes'][n][h]['erreur_standard'], 2)}"
                    for h in ("1min", "5min", "15min")] for n in noms]),
        "table_hypotheses": tableau(
            ["Paramètre", "Valeur", "Statut"],
            [["sigma (pips / √s)", fr(v["calibration"]["sigma_session_londres_pips_par_racine_s"], 3), "MESURÉ sur TRAIN 2010-2018, 03h-12h heure de New York"],
             ["A (exécutions / s à profondeur 0, par côté)", fr(hyp["A"], 2), "hypothèse"],
             ["k (1/pip)", fr(hyp["k"], 1), "hypothèse"],
             ["demi-spread de marché (pip)", fr(hyp["demi_spread_marche"], 2), "hypothèse (EURUSD interbancaire ≈ 0,1-0,3 pip de spread)"],
             ["p (proba de saut après exécution)", fr(hyp["p_adverse"], 2), "hypothèse"],
             ["alpha (taille du saut, pip)", fr(hyp["alpha"], 2), "hypothèse"],
             ["frais (pip / exécution)", fr(hyp["frais"], 3), "hypothèse"],
             ["Q (borne d'inventaire, lots)", str(hyp["Q"]), "choix de conception"],
             ["pas de temps dt", f"{fr(marche['dt'], 1)} s", "choix de conception"],
             ["durée de session", "9 h (03h-12h heure de New York)", "choix de conception"]]),
        "table_placebo": tableau(
            ["bid ET ask touchés", "Sharpe AS", "Sharpe placebo", "PnL moyen/jour AS", "PnL moyen/jour placebo",
             "AS > placebo (Sharpe)", "AS > placebo (PnL moyen)"],
            [["seul le côté perdant" if r == "adverse" else "les deux côtés", fr(placebo[r]["sharpe_ref_moyen"]),
              f"{fr(placebo[r]['sharpe_placebo_moyen'])} (5e-95e pct : {fr(placebo[r]['sharpe_placebo_p5_p95'][0])} ; {fr(placebo[r]['sharpe_placebo_p5_p95'][1])})",
              fr(placebo[r]["pnl_moyen_jour_ref"], 0), fr(placebo[r]["pnl_moyen_jour_placebo"], 0),
              fr(100 * placebo[r]["part_graines_ou_ref_bat_placebo_en_sharpe"], 0) + " % des graines",
              fr(100 * placebo[r]["part_graines_ou_ref_bat_placebo_en_pnl_moyen"], 0) + " % des graines"]
             for r in ("adverse", "deux_cotes")]),
        "table_controle": tableau(
            ["bid ET ask touchés", "Stratégie", "PnL moyen/jour : barres réelles", "PnL moyen/jour : marche aléatoire",
             "markout +1 min : barres réelles", "markout +1 min : marche aléatoire"],
            [["seul le côté perdant" if r == "adverse" else "les deux côtés", n, fr(x["pnl_moyen_jour_reel"], 0),
              fr(x["pnl_moyen_jour_marche_aleatoire"], 0), fr(x["markout_1min_reel"], 2), fr(x["markout_1min_marche_aleatoire"], 2)]
             for r in ("adverse", "deux_cotes") for n, x in ctl["resultats"][r].items()]),
        "ctl_n_jours": str(ctl["n_jours"]),
        "ctl_sigma": fr(ctl["sigma_minute_pips"], 2),
        "n_graines": str(placebo["graines"]),
        "modele_base_nom": f"{modele_base} (traversée >= {fr(seuil_f[modele_base][0], 1)} pip, f = {fr(seuil_f[modele_base][1], 2)})",
        "cumul_haut": tete.musd(max(cumuls)),
        "cumul_bas": tete.musd(min(cumuls)),
        "inv_naif": fr(mc[noms[0]]["inventaire_max_moyen"]),
        "inv_as": fr(mc[noms[1]]["inventaire_max_moyen"]),
        "inv_glft": fr(mc[noms[3]]["inventaire_max_moyen"]),
        "ak_min": fr(min(ak)), "ak_max": fr(max(ak)),
        "pk_min": fr(min(pk)), "pk_max": fr(max(pk)),
    }
    # chiffres isolés utilisés dans la prose
    for i, n in enumerate(["naif", "as", "plafonne", "glft", "placebo"]):
        valeurs[f"sh_{n}"] = fr(mc[noms[i]]["sharpe_annualise"])
        valeurs[f"rj_{n}"] = fr(base_rejeu[noms[i]]["sharpe_annualise"])
    rj_tous = [modeles[m][r][n]["sharpe_annualise"] for m in modeles for r in ("adverse", "deux_cotes") for n in noms]
    valeurs["rj_min"], valeurs["rj_max"] = fr(min(rj_tous)), fr(max(rj_tous))
    sh_L = sens["sharpe_vs_latence"]
    valeurs["lat_max_s"] = fr(sh_L["latence_ms"][-1] / 1000, 0)
    valeurs["as_lat_100ms"] = fr(sh_L["sharpe"][0][1])
    valeurs["as_lat_1s"] = fr(sh_L["sharpe"][sh_L["latence_ms"].index(1000.0)][1])
    valeurs["as_lat_60s"] = fr(sh_L["sharpe"][-1][1])
    valeurs["as_p0"] = fr(sens["sharpe_vs_p_adverse"]["sharpe"][0][1])
    valeurs["as_p04"] = fr(sens["sharpe_vs_p_adverse"]["sharpe"][-1][1])
    valeurs["rj_pnl_jour"] = fr(base_rejeu[noms[0]]["pnl_moyen_pips_lot"], 0)
    valeurs["pla_pnl_ref_adv"] = fr(placebo["adverse"]["pnl_moyen_jour_ref"], 0)
    valeurs["pla_pnl_pla_adv"] = fr(placebo["adverse"]["pnl_moyen_jour_placebo"], 0)
    valeurs["pla_pnl_ref_deux"] = fr(placebo["deux_cotes"]["pnl_moyen_jour_ref"], 0)
    valeurs["pla_pnl_pla_deux"] = fr(placebo["deux_cotes"]["pnl_moyen_jour_placebo"], 0)
    valeurs["pla_win_adv"] = fr(100 * placebo["adverse"]["part_graines_ou_ref_bat_placebo_en_pnl_moyen"], 0)
    valeurs["pla_win_deux"] = fr(100 * placebo["deux_cotes"]["part_graines_ou_ref_bat_placebo_en_pnl_moyen"], 0)
    valeurs["std_as_base"] = fr(base_rejeu[noms[1]]["pnl_ecart_type"], 0)
    valeurs["std_pla_base"] = fr(base_rejeu[noms[4]]["pnl_ecart_type"], 0)
    valeurs["mk_naif_1"] = fr(mk["deux_cotes"][noms[0]]["1min"]["moyenne_pips"], 2)

    # Affirmations qualitatives du modèle de README : si un nouveau run les contredit, on s'arrête plutôt que d'écrire du faux.
    assert max(rj_tous) < 0, "le texte dit qu'aucune convention de rejeu ne donne un Sharpe positif"
    assert max(x["sharpe"] for x in variantes["variantes"]) < 0 and max(cumuls) < 0, "le texte dit qu'aucune des 30 variantes ne gagne"
    assert all(modeles[m][r][noms[0]]["sharpe_annualise"] > modeles[m][r][noms[1]]["sharpe_annualise"]
               for m in modeles for r in ("adverse", "deux_cotes")), "le texte dit que le naïf bat AS dans les six conventions du rejeu"
    assert all(placebo[r]["part_graines_ou_ref_bat_placebo_en_sharpe"] == 0 for r in ("adverse", "deux_cotes")), "texte : AS < placebo en Sharpe dans 100 % des graines"
    assert mc[noms[1]]["sharpe_annualise"] > 2 * mc[noms[0]]["sharpe_annualise"] and mc[noms[3]]["sharpe_annualise"] > mc[noms[1]]["sharpe_annualise"]
    assert sens["sharpe_vs_latence"]["sharpe"][sens["sharpe_vs_latence"]["latence_ms"].index(1000.0)][1] < 0, "texte : AS perd de l'argent à 1 s de latence"
    assert sens["sharpe_vs_latence"]["sharpe"][sens["sharpe_vs_latence"]["latence_ms"].index(500.0)][1] > 0, "texte : AS gagne encore à 0,5 s de latence"
    assert all(x["markout_1min_marche_aleatoire"] < -0.15 and x["pnl_moyen_jour_marche_aleatoire"] < 0
               for r in ctl["resultats"].values() for x in r.values()), "texte : la marche aléatoire sans dérive reproduit un markout et un PnL négatifs"
    mk_deux = [mk["deux_cotes"][n][h]["moyenne_pips"] for n in noms for h in ("1min", "5min", "15min")]
    assert max(mk_deux) < -0.2 and max(mk_deux) - min(mk_deux) < 0.05, "texte : markout négatif et constant de +1 à +15 min"
    assert min(ak) > 0 and min(pk) > 0, "texte : les grilles A x k et p x k restent positives"
    g = sens["sharpe_AS_latence_x_gamma"]
    assert all(x < 0 for x in g["sharpe"][g["latence_ms"].index(1000.0)]) and g["sharpe"][0][-1] > g["sharpe"][0][0], "texte : latence x gamma"

    def remplacer(m):
        cle = m.group(1)
        if cle not in valeurs:
            raise KeyError(f"placeholder inconnu dans le modèle : <<{cle}>>")
        return valeurs[cle]

    modele = (RACINE / "scripts" / "modele_readme.md").read_text(encoding="utf-8")
    return re.sub(r"<<(\w+)>>", remplacer, modele)


def main() -> None:
    texte = construire()
    (RACINE / "README.md").write_bytes(texte.replace("\r\n", "\n").encode("utf-8"))  # LF, même sous Windows
    print("README.md écrit,", len(texte), "caractères")


if __name__ == "__main__":
    main()
