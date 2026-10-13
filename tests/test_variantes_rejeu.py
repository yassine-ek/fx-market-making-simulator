"""Les 30 variantes du rejeu : PnL quotidien exporté, cohérence avec results/verdict_mm.json, calcul de bout en bout."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mm.donnees import ANNEES_VAL, dossier_donnees
from mm.modeles import Strategie, jeu_strategies_base, strategie_placebo
from mm.monte_carlo import sharpe_annualise
from mm.rejeu_reel import N_BARRES, construire_jours, rejouer
from mm.simulateur import Marche, O_NEXEC, O_PNL
from mm.variantes_rejeu import CODE_CONVENTION, CODE_FILL, CODE_STRATEGIE, assembler, calculer_rejeu, drawdown_max

RESULTATS = Path(__file__).resolve().parents[1] / "results"
MOTIF = "données HistData absentes : définir HISTDATA_DIR (voir README, section Reproduire)"


def _json(nom):
    return json.loads((RESULTATS / nom).read_text(encoding="utf-8"))


def test_drawdown_max_valeur_connue():
    assert drawdown_max(np.array([1.0, -2.0, -1.0, 3.0])) == -3.0   # sommet 1, creux -2
    assert drawdown_max(np.array([1.0, 2.0, 3.0])) == 0.0
    assert drawdown_max(np.array([-1.0, -1.0])) == -2.0              # le sommet initial est 0


def test_le_pnl_exporte_redonne_les_sharpe_et_les_executions_de_verdict_mm():
    pnl = pd.read_csv(RESULTATS / "rejeu_pnl_quotidien.csv", index_col=0, parse_dates=True)
    execs = pd.read_csv(RESULTATS / "rejeu_executions_quotidiennes.csv", index_col=0, parse_dates=True)
    meta, verdict = _json("rejeu_variantes.json"), _json("verdict_mm.json")
    par_fill = verdict["rejeu_val"]["par_modele_de_fill"]
    assert list(pnl.columns) == list(execs.columns) == [v["id"] for v in meta["variantes"]]
    assert len(pnl.columns) == 30 == len(set(pnl.columns)) and len(pnl) == verdict["hypotheses"]["rejeu"]["n_jours"]
    assert pnl.index.is_monotonic_increasing and pnl.index.is_unique and pnl.index.max() < pd.Timestamp("2023-01-01")
    for v in meta["variantes"]:
        ref = par_fill[v["modele_fill"]][v["convention"]][v["nom_strategie"]]
        p = pnl[v["id"]].to_numpy()
        assert sharpe_annualise(p) == pytest.approx(ref["sharpe_annualise"], abs=1e-6)
        assert v["sharpe"] == pytest.approx(ref["sharpe_annualise"], abs=1e-9)
        assert p.mean() == pytest.approx(ref["pnl_moyen_pips_lot"], abs=1e-6)
        assert execs[v["id"]].mean() == pytest.approx(ref["executions_moyennes"], abs=1e-9)
        assert v["drawdown_max"] == pytest.approx(drawdown_max(p), rel=1e-8) and v["drawdown_max"] <= 0
        assert 0.0 <= v["dsr"] <= v["psr0"] + 1e-12 or v["dsr"] < 1e-3   # le DSR déflate le PSR (ici tous deux ~ 0)
        assert v["n_essais_dsr"] == 30


def test_un_seul_cas_de_base_par_strategie_probabiliste_cote_perdant():
    variantes = _json("rejeu_variantes.json")["variantes"]
    base = [v for v in variantes if v["base"]]
    assert len(base) == 5 and all(v["modele_fill"] == "probabiliste" and v["convention"] == "adverse" for v in base)
    assert {v["id"].split("-")[0] for v in variantes} == set(CODE_STRATEGIE.values())
    assert {v["id"].split("-")[1] for v in variantes} == set(CODE_FILL.values())
    assert {v["id"].split("-")[2] for v in variantes} == set(CODE_CONVENTION.values())


def _jours_synthetiques(n_jours=4, graine=0):
    rng = np.random.default_rng(graine)
    close = 11000.0 + np.cumsum(rng.standard_normal((n_jours, N_BARRES)) * 2.5, axis=1)
    ouv = np.roll(close, 1, axis=1)
    haut = np.maximum(close + np.abs(rng.standard_normal(close.shape)) * 1.5, ouv)
    bas = np.minimum(close - np.abs(rng.standard_normal(close.shape)) * 1.5, ouv)
    return {"dates": np.datetime64("2019-01-02") + np.arange(n_jours), "O": ouv, "H": haut, "L": bas, "C": close,
            "valide": np.ones(close.shape, bool)}


def test_assembler_donne_30_variantes_coherentes_sur_des_barres_synthetiques():
    marche = Marche(sigma=0.33, A=0.1, k=6.0, p_adverse=0.2, alpha=0.3, demi_spread_liq=0.1, frais=0.005)
    strategies = jeu_strategies_base(0.33, 0.1, 6.0, 20, 32400.0)
    strategies.append(strategie_placebo(strategies[1], 0.175))
    jours = _jours_synthetiques()
    pnl, execs, stats = assembler(calculer_rejeu(jours, strategies, marche), strategies, jours["dates"])
    assert pnl.shape == execs.shape == (4, 30) and len(stats) == 30 and sum(v["base"] for v in stats) == 5
    assert (execs >= 0).all().all() and np.isfinite(pnl.to_numpy()).all()
    for v in stats:
        assert 0.0 <= v["dsr"] <= 1.0 and 0.0 <= v["psr0"] <= 1.0 and v["executions_par_jour"] == pytest.approx(execs[v["id"]].mean())


def _donnees_presentes():
    return (dossier_donnees() / "EURUSD_2022.zip").exists()


@pytest.mark.skipif(not _donnees_presentes(), reason=MOTIF)
def test_le_cas_de_base_AS_recalcule_sur_les_donnees_reelles_redonne_le_csv():
    verdict = _json("verdict_mm.json")
    hyp = verdict["hypotheses"]
    marche = Marche(**hyp["marche_simule"])
    as_ = Strategie(**hyp["strategies"]["Avellaneda-Stoikov"])
    jours = construire_jours(ANNEES_VAL, hyp["hypotheses_non_mesurees"]["demi_spread_marche"])
    sortie = rejouer(jours, as_, marche, 0.1, 0.5, 20260714, False)
    pnl = pd.read_csv(RESULTATS / "rejeu_pnl_quotidien.csv", index_col=0, parse_dates=True)["AS-P-perd"]
    assert np.abs(sortie[:, O_PNL] - pnl.to_numpy()).max() < 1e-4   # arrondi du CSV à 10 chiffres significatifs
    assert [str(d) for d in jours["dates"].astype("datetime64[D]")[:3]] == [str(d.date()) for d in pnl.index[:3]]
    assert sortie[:, O_NEXEC].mean() == pytest.approx(verdict["rejeu_val"]["base"]["Avellaneda-Stoikov"]["executions_moyennes"], abs=1e-9)
