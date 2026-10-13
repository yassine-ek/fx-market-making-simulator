"""Figures « vitrine » du README : hero_equity.png, toutes_variantes.png, overfit_scatter.png.

Lit UNIQUEMENT results/rejeu_pnl_quotidien.csv, results/rejeu_variantes.json et results/verdict_mm.json : aucune donnée de
marché, TEST jamais chargé (le CSV s'arrête au 2022-12-30). PnL NET de frais d'exécution et de liquidation, cumulé en
millions de USD (1 pip x 1 lot = 100 USD). Cas de base = modèle de fill « probabiliste » (traversée >= 0,1 pip, f = 0,5), côté
perdant seul quand bid ET ask sont touchés.

Usage : python scripts/generer_figures_vitrine.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from mm.figures import COULEURS  # noqa: E402
from mm.variantes_rejeu import CAPITAL_REF_USD, CODE_STRATEGIE, FIN_SELECTION, LIBELLE_CONVENTION, USD_PAR_PIP_LOT  # noqa: E402

RESULTATS, FIGURES = RACINE / "results", RACINE / "figures"
DPI = 130
GRIS_ZONE = "#e7e9ee"
MODELE_STRATEGIE = {v: k for k, v in CODE_STRATEGIE.items()}  # "AS" -> "as"
MARQUEURS_FILL = {"touche": "o", "traversee": "s", "probabiliste": "^"}


def f2(x: float, d: int = 1) -> str:
    return f"{x:.{d}f}".replace(".", ",").replace("-", "−")


def charger():
    verdict = json.loads((RESULTATS / "verdict_mm.json").read_text(encoding="utf-8"))
    meta = json.loads((RESULTATS / "rejeu_variantes.json").read_text(encoding="utf-8"))
    pnl = pd.read_csv(RESULTATS / "rejeu_pnl_quotidien.csv", index_col=0, parse_dates=True)
    assert pnl.index.max() < pd.Timestamp("2023-01-01"), "TEST interdit"
    return verdict, meta["variantes"], pnl


def cumul_musd(pnl: pd.DataFrame, vid: str) -> pd.Series:
    """PnL cumulé en M USD, avec un point de départ à 0 la veille du premier jour."""
    c = pnl[vid].cumsum() * USD_PAR_PIP_LOT / 1e6
    return pd.concat([pd.Series([0.0], index=[c.index[0] - pd.Timedelta(days=1)]), c])


def drawdown_musd(c: pd.Series) -> pd.Series:
    return c - c.cummax()


def ligne_frais(verdict: dict) -> str:
    h = verdict["hypotheses"]["hypotheses_non_mesurees"]
    return (f"frais {f2(h['frais'], 3)} pip/exécution + demi-spread de liquidation {f2(h['demi_spread_marche'], 2)} pip (hypothèses) ; "
            f"demi-spread de marché {f2(h['demi_spread_marche'], 2)} pip sur prix BID ; fill probabiliste (traversée ≥ 0,1 pip, f = 0,5), "
            f"côté perdant seul ; 1 pip × lot = 100 USD")


def _zones(ax, debut, fin):
    fin_sel = pd.Timestamp(FIN_SELECTION)
    ax.axvspan(debut, fin_sel, color=GRIS_ZONE, zorder=0)
    ax.axvline(fin_sel + pd.Timedelta(days=1), color="0.35", ls="--", lw=1, zorder=1)


def _base(variantes):
    return [v for v in variantes if v["base"]]


def hero(verdict, variantes, pnl):
    """Figure héro lisible une fois réduite : 2 panneaux, 10 x 5,8 pouces, aucun texte sous 11 pt, titre court."""
    base = _base(variantes)
    capital_musd = CAPITAL_REF_USD / 1e6  # capital de référence ARBITRAIRE du tableau de bord
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10, 5.8), sharex=True, gridspec_kw={"height_ratios": [3, 1.3], "hspace": 0.08})
    debut, fin = pnl.index[0] - pd.Timedelta(days=1), pnl.index[-1]
    _zones(ax, debut, fin)
    _zones(ax2, debut, fin)
    finaux = []
    for v in base:
        modele = MODELE_STRATEGIE[v["id"].split("-")[0]]
        c = cumul_musd(pnl, v["id"])
        ax.plot(c.index, c.values, color=COULEURS[modele], lw=2.2, label=f"{v['strategie']} (Sharpe {f2(v['sharpe'])})")
        ax2.plot(c.index, drawdown_musd(c).values, color=COULEURS[modele], lw=1.6)
        finaux.append(c.iloc[-1])
    ax.axhline(0, color="0.2", lw=0.8)
    ax.set_ylim(min(finaux) * 1.15, -min(finaux) * 0.17)  # un peu de place au-dessus de zéro pour les étiquettes de période
    ax.set_ylabel("PnL cumulé net (M USD)", fontsize=12)
    ax.tick_params(labelsize=11)
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=11, title="Sharpe annualisé du rejeu", title_fontsize=11)
    trans = ax.get_xaxis_transform()
    fin_sel = pd.Timestamp(FIN_SELECTION)
    ax.text(debut + (fin_sel - debut) / 2, 0.98, "2019-2020 : sélection", transform=trans, ha="center", va="top", fontsize=11)
    ax.text(fin_sel + (fin - fin_sel) / 2, 0.98, "2021-2022 : évaluation", transform=trans, ha="center", va="top", fontsize=11)
    ax.text(0.99, 0.80, f"cumul final : de {f2(min(finaux))} à {f2(max(finaux))} M USD\n"
            f"≈ {f2(min(finaux) / capital_musd * 100, 0)} % du capital de référence\n(arbitraire : {capital_musd:.0f} M USD)",
            transform=ax.transAxes, ha="right", va="top", fontsize=11, color="0.25")
    ax2.set_ylabel("drawdown (M USD)", fontsize=12)
    ax2.tick_params(labelsize=11)
    ax2.grid(alpha=0.3)
    fig.suptitle("Rejeu EURUSD 1 min, VAL 2019-2022 : PnL cumulé net", fontsize=13.5, y=0.995)
    ax.set_title("5 stratégies, cas de base (fill probabiliste, côté perdant seul)", fontsize=11, color="0.25", pad=6)
    fig.savefig(FIGURES / "hero_equity.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def toutes_variantes(verdict, variantes, pnl):
    fig, ax = plt.subplots(figsize=(11, 6.2))
    debut, fin = pnl.index[0] - pd.Timedelta(days=1), pnl.index[-1]
    _zones(ax, debut, fin)
    for v in variantes:
        if not v["base"]:
            c = cumul_musd(pnl, v["id"])
            ax.plot(c.index, c.values, color="0.6", lw=0.9, alpha=0.9)
    etiquettes = []
    for v in _base(variantes):
        modele = MODELE_STRATEGIE[v["id"].split("-")[0]]
        c = cumul_musd(pnl, v["id"])
        ax.plot(c.index, c.values, color=COULEURS[modele], lw=2.4, zorder=5)
        etiquettes.append((c.iloc[-1], v["strategie"], COULEURS[modele]))
    ax.plot([], [], color="0.6", lw=0.9, label="25 autres variantes (autres modèles de fill, autre convention)")
    ax.plot([], [], color="0.2", lw=2.4, label="cas de base (probabiliste, côté perdant seul), 5 stratégies en couleur")
    ax.axhline(0, color="0.2", lw=0.8)
    # les 5 courbes du cas de base sont quasi confondues : une seule étiquette, avec leur plage de valeurs finales
    finaux = [e[0] for e in etiquettes]
    ax.text(fin + pd.Timedelta(days=15), float(np.mean(finaux)), f"cas de base\n{f2(min(finaux))} à {f2(max(finaux))}\nM USD", va="center", fontsize=8.5,
            fontweight="bold", color="0.2")
    ax.set_xlim(debut, fin + pd.Timedelta(days=260))
    ax.set_ylabel("PnL cumulé net (M USD)")
    ax.grid(alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)
    trans = ax.get_xaxis_transform()
    fin_sel = pd.Timestamp(FIN_SELECTION)
    ax.text(debut + (fin_sel - debut) / 2, 0.97, "2019-2020 (sélection)", transform=trans, ha="center", va="top", fontsize=10)
    ax.text(fin_sel + (fin - fin_sel) / 2, 0.97, "2021-2022 (évaluation)", transform=trans, ha="center", va="top", fontsize=10)
    fig.suptitle("Toutes les variantes testées : 30 rejeux (5 stratégies × 3 modèles de fill × 2 conventions), nets de frais, rien n'est écarté",
                 fontsize=12, y=0.99)
    ax.set_title(ligne_frais(verdict), fontsize=8.6, color="0.25", pad=6)
    fig.savefig(FIGURES / "toutes_variantes.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def overfit_scatter(verdict, variantes):
    sim = {n: m["sharpe_annualise"] for n, m in verdict["monte_carlo"].items()}
    fig, ax = plt.subplots(figsize=(8.4, 6.6))
    lim = (-28, 42)
    g = np.linspace(*lim, 200)
    ax.fill_between(g, lim[0], g, color="#b91c1c", alpha=0.06, lw=0)
    ax.plot(g, g, color="0.4", ls="--", lw=1, label="Sharpe rejeu = Sharpe simulé (aucun écart)")
    ax.axhline(0, color="0.2", lw=0.8)
    for v in variantes:
        modele = MODELE_STRATEGIE[v["id"].split("-")[0]]
        x, y = sim[v["nom_strategie"]], v["sharpe"]
        plein = v["convention"] == "adverse"
        ax.errorbar([x], [y], yerr=[[y - v["sharpe_ic95_blocs"][0]], [v["sharpe_ic95_blocs"][1] - y]], fmt="none", ecolor=COULEURS[modele],
                    alpha=0.35, lw=1, zorder=2)
        ax.scatter([x], [y], s=70, marker=MARQUEURS_FILL[v["modele_fill"]], facecolor=COULEURS[modele] if plein else "white",
                   edgecolor=COULEURS[modele], linewidth=1.5, zorder=4)
    par_strategie = {v["id"].split("-")[0]: v for v in variantes}  # un représentant par stratégie
    legende = [Line2D([], [], marker="o", ls="", color=COULEURS[m], markerfacecolor=COULEURS[m], markersize=9,
                      label=f"{par_strategie[c]['strategie']} (simulé {f2(sim[par_strategie[c]['nom_strategie']])})")
               for c, m in MODELE_STRATEGIE.items()]
    legende += [Line2D([], [], marker=m, ls="", color="0.3", markerfacecolor="0.3", label=f"modèle de fill : {k.replace('traversee', 'traversée')}") for k, m in MARQUEURS_FILL.items()]
    legende += [Line2D([], [], marker="o", ls="", color="0.3", markerfacecolor="0.3", label=f"plein : {LIBELLE_CONVENTION['adverse']}"),
                Line2D([], [], marker="o", ls="", color="0.3", markerfacecolor="white", label=f"creux : {LIBELLE_CONVENTION['deux_cotes']}")]
    h0, l0 = ax.get_legend_handles_labels()
    ax.legend(handles=h0 + legende, loc="upper left", fontsize=8.5)
    ax.set_xlim(0, 42)
    ax.set_ylim(*lim)
    ax.set_xlabel("Sharpe annualisé en SIMULATION (Monte Carlo, 2 000 sessions)")
    ax.set_ylabel("Sharpe annualisé du REJEU sur EURUSD réel (VAL 2019-2022)")
    ax.grid(alpha=0.3)
    ax.text(0.98, 0.04, "zone rose : le réel fait pire que la simulation", transform=ax.transAxes, ha="right", fontsize=8.5, color="#7f1d1d")
    ax.set_title("Overfit ? Sharpe simulé contre Sharpe du rejeu réel, une variante = un point\n"
                 "(30 variantes, barres verticales = IC 95 % par blocs de 10 jours ; ici « hors échantillon » = le marché réel)", fontsize=10.5)
    fig.savefig(FIGURES / "overfit_scatter.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    verdict, variantes, pnl = charger()
    hero(verdict, variantes, pnl)
    toutes_variantes(verdict, variantes, pnl)
    overfit_scatter(verdict, variantes)
    print("figures/hero_equity.png, toutes_variantes.png, overfit_scatter.png écrites")


if __name__ == "__main__":
    main()
