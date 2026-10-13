"""Cohérence des sorties « vitrine » : tableau de bord (docs/), README généré depuis results/, hygiène des chemins.

Aucune donnée de marché requise : tout est lu dans results/ (versionné)."""
import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

RACINE = Path(__file__).resolve().parents[1]
DOCS = RACINE / "docs"
RESULTATS = RACINE / "results"
GABARIT = RACINE.parent / "_outils" / "dashboard" / "index.html"
USD_PAR_PIP_LOT, CAPITAL_REF_USD = 100.0, 100e6


def _json(chemin: Path) -> dict:
    return json.loads(chemin.read_text(encoding="utf-8"))


def _module(nom: str):
    spec = importlib.util.spec_from_file_location(nom, RACINE / "scripts" / f"{nom}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_donnees_du_tableau_de_bord_coherentes_et_sans_test():
    d = _json(DOCS / "data.json")
    pnl = pd.read_csv(RESULTATS / "rejeu_pnl_quotidien.csv", index_col=0, parse_dates=True)
    execs = pd.read_csv(RESULTATS / "rejeu_executions_quotidiennes.csv", index_col=0, parse_dates=True)
    assert d["frontieres"] == {"train_fin": "2020-12-31", "val_fin": "2022-12-31"}
    assert d["libelles"] == {"train": "SÉLECTION 2019-2020", "val": "ÉVALUATION 2021-2022"}
    assert pd.Timestamp(d["dates"][-1]) < pd.Timestamp("2023-01-01"), "le TEST ne doit jamais apparaître"
    assert [v["id"] for v in d["variantes"]] == list(pnl.columns) and len(d["variantes"]) == 30
    dates = pd.DatetimeIndex(d["dates"])
    assert list(dates) == list(pnl.index)
    sel = dates <= pd.Timestamp(d["frontieres"]["train_fin"])
    for v in d["variantes"]:
        r = np.array(v["rendements"], dtype=float)
        assert len(r) == len(dates) and not v.get("reference")
        attendu = pnl[v["id"]].to_numpy() * USD_PAR_PIP_LOT / CAPITAL_REF_USD
        assert np.abs(r - attendu).max() < 1e-9                                       # arrondi à 8 chiffres significatifs
        assert abs(r[sel].mean() / r[sel].std(ddof=1) * np.sqrt(252) - v["stats"]["sharpe_train"]) < 1e-3
        assert v["stats"]["nb_trades_train"] == int(execs[v["id"]].to_numpy()[sel].sum())
        assert v["stats"]["nb_trades_val"] == int(execs[v["id"]].to_numpy()[~sel].sum())
    for f in d["filtres"]:
        assert f["type"] in {"min", "max", "choix"}
    cles = {f["cle"] for f in d["filtres"]}
    assert {"nb_trades_train", "sharpe_train", "strategie", "modele_fill", "convention"} <= cles


def test_data_js_identique_a_data_json():
    brut = (DOCS / "data.json").read_text(encoding="utf-8")
    assert (DOCS / "data.js").read_text(encoding="utf-8") == "window.DATA = " + brut + ";\n"
    assert (DOCS / ".nojekyll").exists()


def test_page_du_tableau_de_bord_identique_au_gabarit_commun():
    if not GABARIT.exists():
        return  # dépôt isolé : pas de gabarit à côté
    assert (DOCS / "index.html").read_bytes() == GABARIT.read_bytes()


def test_blocs_de_chiffres_du_readme_lus_dans_results():
    mod = _module("generer_readme_tete")
    verdict, variantes = mod.charger()
    texte = (RACINE / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    for nom, contenu in mod.blocs(verdict, variantes).items():
        m = re.search(rf"<!-- AUTO:{nom} -->\n(.*?)\n<!-- /AUTO:{nom} -->", texte, re.S)
        assert m, f"balises AUTO:{nom} absentes du README"
        assert m.group(1) == contenu, f"bloc AUTO:{nom} périmé : relancer scripts/generer_readme.py"


def test_readme_entier_identique_a_ce_que_genere_le_script():
    texte = (RACINE / "README.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    assert texte == _module("generer_readme").construire(), "README périmé : relancer scripts/generer_readme.py"


def test_chaque_dossier_a_son_readme():
    for dossier in ("mm", "tests", "scripts", "notebooks", "figures", "results", "docs"):
        assert (RACINE / dossier / "README.md").is_file(), dossier


def test_les_readme_de_dossier_citent_tous_les_fichiers():
    for dossier in ("mm", "tests", "scripts", "notebooks", "figures", "results", "docs"):
        texte = (RACINE / dossier / "README.md").read_text(encoding="utf-8")
        for f in sorted((RACINE / dossier).iterdir()):
            if f.is_file() and f.name != "README.md" and not f.name.startswith("__"):
                assert f"`{f.name}`" in texte, f"{dossier}/README.md ne décrit pas {f.name}"


def test_aucun_chemin_absolu_de_machine_dans_le_depot():
    """Pas de chemin absolu de machine (lecteur, puis dossier Users) dans le code, les notebooks, les README et les résultats."""
    motif = re.compile(r"[A-Za-z]:[\\/]+Users")
    exclus = {"test_dashboard_et_readme.py"}
    fautifs = []
    for p in RACINE.rglob("*"):
        if (not p.is_file() or p.name in exclus or p.suffix not in {".py", ".md", ".json", ".ipynb", ".yml", ".txt", ".csv", ".js", ".html"}
                or any(x in p.parts for x in ("__pycache__", ".pytest_cache", "histdata", ".git", "_rapide"))):
            continue
        if motif.search(p.read_text(encoding="utf-8", errors="ignore")):
            fautifs.append(str(p.relative_to(RACINE)))
    assert not fautifs, fautifs
