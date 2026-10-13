"""Relance tout : calibration TRAIN, Monte Carlo, sensibilités, rejeu VAL, figures, results/verdict_mm.json et results/rejeu_*.

    python scripts/run_all.py            # quelques minutes (2 000 sessions, sensibilités à 500 sessions)
    python scripts/run_all.py --rapide   # ~1 min, pour vérifier que la chaîne tourne (écrit dans des sous-dossiers _rapide)
"""
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from mm import figures  # noqa: E402
from mm.calibration import SESSION_LONDRES, Hypotheses, grille_sensibilite_Ak, sigma_par_heure, sigma_session  # noqa: E402
from mm.donnees import ANNEE_TEST_DEBUT, ANNEE_TRAIN_FIN, ANNEES_VAL, DonneesManquantes, verifier_donnees  # noqa: E402
import numpy as np  # noqa: E402

from mm.modeles import jeu_strategies_base, strategie_placebo  # noqa: E402
from mm.monte_carlo import balayage_1d, grille_2d, grille_A_k, monte_carlo, resumer  # noqa: E402
from mm.rejeu_reel import (MODELE_BASE, MODELES_FILL, comparer_placebo_rejeu, construire_jours, jours_marche_aleatoire, rejouer,  # noqa: E402
                           resume_markout, sensibilite_rejeu)
from mm.simulateur import O_PNL, Marche, simuler_trajectoire  # noqa: E402
from mm.variantes_rejeu import CONVENTIONS, assembler, calculer_rejeu, ecrire as ecrire_variantes  # noqa: E402

GRAINE_MC, GRAINE_SENS, GRAINE_REJEU = 20260713, 777, 20260714
BLOC_JOURS = 10  # bootstrap par blocs du rejeu : 2 semaines de bourse, fixé a priori
N_GRAINES_PLACEBO = 30


def main(rapide=False):
    verifier_donnees([*range(2010, ANNEE_TRAIN_FIN + 1), *ANNEES_VAL])  # TRAIN 2010-2018 et VAL 2019-2022 ; message clair si elles manquent
    debut = time.time()
    n_mc, n_sens = (150, 60) if rapide else (2000, 500)
    dossier_res, dossier_fig = RACINE / "results", RACINE / "figures"
    if rapide:  # un essai rapide n'écrase jamais les vrais résultats
        dossier_res, dossier_fig = dossier_res / "_rapide", dossier_fig / "_rapide"
    dossier_res.mkdir(parents=True, exist_ok=True)
    dossier_fig.mkdir(parents=True, exist_ok=True)

    def etape(nom):
        print(f"[{time.time() - debut:6.0f}s] {nom}", flush=True)

    # 1. calibration (TRAIN) + hypothèses
    etape("calibration de sigma sur TRAIN 2010-2018")
    h = Hypotheses()
    sigma_h = sigma_par_heure()
    sigma = sigma_session(sigma_h)
    marche = Marche(sigma=sigma, A=h.A, k=h.k, p_adverse=h.p_adverse, alpha=h.alpha,
                    demi_spread_liq=h.demi_spread_marche, frais=h.frais, dt=0.1)
    strategies = jeu_strategies_base(sigma, h.A, h.k, h.Q, marche.duree, h.latence_pas)
    as_ = next(s for s in strategies if s.modele == "as")
    # placebo : largeur moyenne des cotes AS mesurée sur une session pilote (graine à part, hors des sessions évaluées)
    pilote = simuler_trajectoire(as_, marche, GRAINE_MC + 1, 0)
    demi_moyen_as = float(np.mean((pilote["ask"] - pilote["bid"]) / 2.0))
    strategies.append(strategie_placebo(as_, demi_moyen_as))
    noms = [s.nom for s in strategies]
    figures.sigma_par_heure(sigma_h, SESSION_LONDRES, dossier_fig)

    # 2. Monte Carlo principal
    etape(f"Monte Carlo : {n_mc} sessions x {len(strategies)} stratégies")
    res = monte_carlo(strategies, marche, n_mc, GRAINE_MC)
    resumes = [resumer(res[i]) for i in range(len(strategies))]
    pnl = [res[i, :, O_PNL] for i in range(len(strategies))]
    trajectoires = [simuler_trajectoire(s, marche, GRAINE_MC, 0) for s in strategies]
    figures.trajectoire_exemple(trajectoires, strategies, dossier_fig)
    figures.distributions_pnl(pnl, strategies, dossier_fig)
    figures.decomposition_pnl(resumes, strategies, dossier_fig)

    # 3. sensibilités (robustesse, pas optimisation : grilles grossières)
    p_vals, k_vals = [0.0, 0.1, 0.2, 0.3, 0.4], [4.0, 5.0, 6.0, 8.0, 10.0]
    L_vals, g_facteurs = [1, 2, 5, 10, 30], [0.25, 0.5, 1.0, 2.0, 4.0]
    L_vals_1d = L_vals + [100, 600]  # jusqu'à 60 s : la latence implicite d'un rejeu sur barres 1 min
    etape("heatmap p adverse x k")
    sh_pk, _ = grille_2d(as_, marche, ("marche", "p_adverse", p_vals), ("marche", "k", k_vals), n_sens, GRAINE_SENS)
    figures.heatmap_simple(sh_pk, [f"{k:g}" for k in k_vals], [f"{p:g}" for p in p_vals],
                           "Avellaneda-Stoikov : Sharpe annualisé simulé",
                           "k RÉEL du marché (la stratégie croit k=6)", "probabilité de sélection adverse p",
                           dossier_fig, "heatmap_p_k.png", marque=(2, 2))
    etape("heatmap latence x gamma")
    gammas = [as_.gamma * g for g in g_facteurs]
    sh_lg, _ = grille_2d(as_, marche, ("strategie", "latence_pas", L_vals), ("strategie", "gamma", gammas), n_sens, GRAINE_SENS)
    figures.heatmap_simple(sh_lg, [f"{g:.1e}" for g in gammas], [f"{int(L * marche.dt * 1000)} ms" for L in L_vals],
                           "Avellaneda-Stoikov : Sharpe annualisé simulé",
                           "gamma (x0,25 à x4 autour de la valeur de base)", "latence : délai entre deux mises à jour des cotes",
                           dossier_fig, "heatmap_latence_gamma.png", marque=(0, 2))
    etape("grille A x k (3x3)")
    valeurs_A, valeurs_k = grille_sensibilite_Ak(h)
    sh_ak = grille_A_k(strategies, marche, valeurs_A, valeurs_k, n_sens, GRAINE_SENS)
    figures.heatmaps_A_k(sh_ak, strategies, valeurs_A, valeurs_k, dossier_fig)
    etape("effondrement du Sharpe : p et latence, toutes stratégies")
    sh_p, _ = balayage_1d(strategies, marche, "p_adverse", p_vals, n_sens, GRAINE_SENS)
    sh_L, _ = balayage_1d(strategies, marche, "latence_pas", L_vals_1d, n_sens, GRAINE_SENS, cote="strategie")
    latences_ms = [L * marche.dt * 1000 for L in L_vals_1d]
    figures.sharpe_effondrement(p_vals, sh_p, latences_ms, sh_L, strategies, dossier_fig)

    # 4. rejeu sur barres réelles VAL (aucune donnée 2023+ n'est lue : donnees.py l'interdit)
    etape("rejeu VAL 2019-2022 : 3 modèles de fill x 2 résolutions bid+ask x 5 stratégies")
    jours = construire_jours(ANNEES_VAL, h.demi_spread_marche)
    dates = jours["dates"].astype("datetime64[D]")
    resolutions = CONVENTIONS
    rejeu = calculer_rejeu(jours, strategies, marche, GRAINE_REJEU)
    resumes_fill = {k: [resumer(x[0], bloc=BLOC_JOURS) for x in v] for k, v in rejeu.items()}
    noms_fill = list(MODELES_FILL)
    etiquettes_fill = [f"{m} (traversée >= {MODELES_FILL[m][0]} pip, f={MODELES_FILL[m][1]})" for m in noms_fill]
    figures.rejeu_modeles_fill(
        {r: ([[x["sharpe_annualise"] for x in resumes_fill[(m, r)]] for m in noms_fill],
             [[x["sharpe_ic95"][0] for x in resumes_fill[(m, r)]] for m in noms_fill],
             [[x["sharpe_ic95"][1] for x in resumes_fill[(m, r)]] for m in noms_fill]) for r in resolutions},
        etiquettes_fill, strategies, dossier_fig)
    res_base, resumes_rejeu = rejeu[(MODELE_BASE, "adverse")], resumes_fill[(MODELE_BASE, "adverse")]
    figures.rejeu_pnl_cumule(dates, {r: [x[0][:, O_PNL] for x in rejeu[(MODELE_BASE, r)]] for r in resolutions},
                             strategies, dossier_fig)
    markouts = {r: [resume_markout(x[1]) for x in rejeu[(MODELE_BASE, r)]] for r in resolutions}
    figures.markout_rejeu(markouts, strategies, dossier_fig)
    etape(f"placebo : {N_GRAINES_PLACEBO} graines")
    seuil_b, f_b = MODELES_FILL[MODELE_BASE]
    graines = [GRAINE_REJEU + 1 + i for i in range(N_GRAINES_PLACEBO)]
    cmp_pla = {r: comparer_placebo_rejeu(jours, as_, strategies[-1], marche, seuil_b, f_b, graines, deux)
               for r, deux in resolutions.items()}
    figures.placebo_rejeu(cmp_pla, as_.nom, dossier_fig)
    fs, seuils = [0.25, 0.5, 0.75, 1.0], [-0.1, 0.0, 0.1, 0.3]
    sens_rejeu = sensibilite_rejeu(jours, strategies, marche, fs, seuils, GRAINE_REJEU)
    figures.rejeu_sensibilite(sens_rejeu[:, :, noms.index(as_.nom)], fs, seuils, as_.nom, dossier_fig)

    # contrôle : le même rejeu sur une marche aléatoire SANS dérive ni sélection adverse, de même sigma de minute que VAL
    etape("contrôle : rejeu sur marche aléatoire sans dérive (même sigma de minute que VAL)")
    sigma_min_val = float(np.diff(jours["C"], axis=1).std())
    n_synth = 60 if rapide else 400
    synth = jours_marche_aleatoire(n_synth, sigma_min_val, GRAINE_REJEU)
    controle = {}
    for r, deux in resolutions.items():
        controle[r] = {}
        for s in (strategies[0], as_):
            sortie, mko, _, _ = rejouer(synth, s, marche, seuil_b, f_b, GRAINE_REJEU, deux, detail=True)
            vrai = rejeu[(MODELE_BASE, r)][noms.index(s.nom)]
            controle[r][s.nom] = {"pnl_moyen_jour_marche_aleatoire": float(sortie[:, O_PNL].mean()),
                                  "markout_1min_marche_aleatoire": resume_markout(mko)["1min"]["moyenne_pips"],
                                  "pnl_moyen_jour_reel": float(vrai[0][:, O_PNL].mean()),
                                  "markout_1min_reel": resume_markout(vrai[1])["1min"]["moyenne_pips"]}

    # 5. verdict JSON
    verdict = {
        "meta": {"graines": {"monte_carlo": GRAINE_MC, "sensibilites": GRAINE_SENS, "rejeu": GRAINE_REJEU},
                 "n_sessions_monte_carlo": n_mc, "n_sessions_sensibilites": n_sens,
                 "unites": "prix en pips, PnL en pips x lot (1 pip x 1 lot = 100 USD), Sharpe journalier x sqrt(252)",
                 "split": {"train": "<= 2018 (calibration de sigma uniquement)", "val": "2019-2022 (rejeu)",
                           "test": f">= {ANNEE_TEST_DEBUT} : scellé, jamais lu"},
                 "mode_rapide": rapide},
        "calibration": {"sigma_session_londres_pips_par_racine_s": sigma,
                        "sigma_par_heure_est": {str(i): float(v) for i, v in enumerate(sigma_h)},
                        "periode": "2010-2018, variations de close 1 min consécutives"},
        "hypotheses": {"marche_simule": asdict(marche), "hypotheses_non_mesurees": asdict(h),
                       "strategies": {s.nom: asdict(s) for s in strategies},
                       "placebo_demi_spread_moyen_pips": demi_moyen_as,
                       "rejeu": {"modeles_fill (seuil_pips, f)": {m: list(v) for m, v in MODELES_FILL.items()},
                                 "modele_de_base": MODELE_BASE + " + adverse",
                                 "ordre_si_bid_et_ask_touches": "défavorable : côté perdant d'abord ; "
                                 "adverse = lui seul est exécuté (pessimiste), deux_cotes = l'autre aussi (optimiste)",
                                 "demi_spread_marche": h.demi_spread_marche, "session": "03h00-12h00 heure de New York",
                                 "n_jours": int(len(dates)),
                                 "reference_causale": "close de la minute précédente (+ demi-spread : HistData est en BID)"}},
        "monte_carlo": dict(zip(noms, resumes)),
        "sensibilites_monte_carlo": {
            "sharpe_AS_p_adverse_x_k_reel": {"p": p_vals, "k": k_vals, "sharpe": sh_pk.tolist()},
            "sharpe_AS_latence_x_gamma": {"latence_ms": [L * marche.dt * 1000 for L in L_vals], "gamma": gammas, "sharpe": sh_lg.tolist()},
            "sharpe_A_x_k_reels": {"A": valeurs_A, "k": valeurs_k, "strategies": noms, "sharpe": sh_ak.tolist()},
            "sharpe_vs_p_adverse": {"p": p_vals, "strategies": noms, "sharpe": sh_p.tolist()},
            "sharpe_vs_latence": {"latence_ms": latences_ms, "strategies": noms, "sharpe": sh_L.tolist()}},
        "rejeu_val": {"modele_de_base": MODELE_BASE, "base": dict(zip(noms, resumes_rejeu)),
                      "par_modele_de_fill": {m: {r: dict(zip(noms, resumes_fill[(m, r)])) for r in resolutions}
                                             for m in noms_fill},
                      "markout_par_execution_pips (modele de base)": {r: dict(zip(noms, markouts[r])) for r in resolutions},
                      "placebo": {"graines": N_GRAINES_PLACEBO, "strategie_de_reference": as_.nom,
                                  **{r: {"sharpe_ref_moyen": float(c["ref"][0].mean()),
                                         "sharpe_placebo_moyen": float(c["placebo"][0].mean()),
                                         "sharpe_placebo_p5_p95": [float(x) for x in np.percentile(c["placebo"][0], [5, 95])],
                                         "part_graines_ou_ref_bat_placebo_en_sharpe": float((c["ref"][0] > c["placebo"][0]).mean()),
                                         "pnl_moyen_jour_ref": float(c["ref"][1].mean()),
                                         "pnl_moyen_jour_placebo": float(c["placebo"][1].mean()),
                                         "part_graines_ou_ref_bat_placebo_en_pnl_moyen": float((c["ref"][1] > c["placebo"][1]).mean())}
                                     for r, c in cmp_pla.items()}},
                      "sensibilite_f_seuil": {"f": fs, "seuil_pips": seuils, "strategies": noms,
                                              "sharpe": sens_rejeu.tolist()},
                       "controle_marche_aleatoire": {
                           "description": "même rejeu (modèle de base) sur des journées de marche aléatoire sans dérive ni sélection adverse",
                           "sigma_minute_pips": sigma_min_val, "n_jours": n_synth, "pas_sous_minute_s": 1, "resultats": controle}},
    }
    (dossier_res / "verdict_mm.json").write_text(json.dumps(verdict, indent=2, ensure_ascii=False), encoding="utf-8")
    # PnL quotidien des 30 variantes du rejeu (source du tableau de bord, de la figure héro et des tableaux du README)
    etape("PnL quotidien des 30 variantes -> results/rejeu_*")
    pnl_var, exec_var, stats_var = assembler(rejeu, strategies, dates)
    ecrire_variantes(dossier_res, pnl_var, exec_var, stats_var, marche)

    print("\nSharpe annualisé : Monte Carlo [IC95] | rejeu VAL, côté perdant seul (touche/traversée/probabiliste) | deux côtés")
    for j, (n, a) in enumerate(zip(noms, resumes)):
        rj = "  ".join(f"{resumes_fill[(m, 'adverse')][j]['sharpe_annualise']:6.1f}" for m in noms_fill)
        rj += "  |  " + "  ".join(f"{resumes_fill[(m, 'deux_cotes')][j]['sharpe_annualise']:6.1f}" for m in noms_fill)
        print(f"{n:28s} {a['sharpe_annualise']:6.1f} [{a['sharpe_ic95'][0]:5.1f};{a['sharpe_ic95'][1]:5.1f}]  {rj}")
    etape("terminé")


if __name__ == "__main__":
    try:
        main(rapide="--rapide" in sys.argv)
    except DonneesManquantes as e:
        sys.exit(f"ERREUR : {e}")  # message d'aide, pas de trace brute
