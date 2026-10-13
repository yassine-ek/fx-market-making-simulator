"""Figures PNG (dpi 130). Une fonction par figure, aucune logique de calcul ici."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

DPI = 130
COULEURS = {"naif": "#7f7f7f", "as": "#1f77b4", "as_plafonne": "#ff7f0e", "glft": "#2ca02c", "placebo": "#9467bd"}


def _couleur(strategie):
    return COULEURS[strategie.modele]


def _sauver(fig, dossier, nom):
    fig.savefig(Path(dossier) / nom, dpi=DPI, bbox_inches="tight")
    plt.close(fig)


def trajectoire_exemple(trajectoires, strategies, dossier, fenetre=(3600.0, 3720.0)):
    """Haut : mid, cotes et exécutions de la stratégie AS sur 2 min. Milieu : son inventaire. Bas : inventaire de la session entière, 4 stratégies."""
    fig, axes = plt.subplots(3, 1, figsize=(10, 10), gridspec_kw={"height_ratios": [3, 1.3, 2]})
    i_as = next(i for i, s in enumerate(strategies) if s.modele == "as")
    tr = trajectoires[i_as]
    m = (tr["temps"] >= fenetre[0]) & (tr["temps"] < fenetre[1])
    t = tr["temps"][m] / 60.0
    ax = axes[0]
    ax.plot(t, tr["mid"][m], color="black", lw=0.8, label="mid (simulé)")
    ax.plot(t, tr["bid"][m], color="#2ca02c", lw=0.7, drawstyle="steps-post", label="cote bid")
    ax.plot(t, tr["ask"][m], color="#d62728", lw=0.7, drawstyle="steps-post", label="cote ask")
    f = tr["executions"][m]
    ax.scatter(t[(f & 1) > 0], tr["bid"][m][(f & 1) > 0], marker="^", color="#2ca02c", s=40, zorder=3, label="exécution bid (achat)")
    ax.scatter(t[(f & 2) > 0], tr["ask"][m][(f & 2) > 0], marker="v", color="#d62728", s=40, zorder=3, label="exécution ask (vente)")
    ax.set_ylabel("prix relatif (pips)")
    ax.set_title("Avellaneda-Stoikov : 2 minutes d'une session simulée (cotes recalculées à chaque pas de 0,1 s)")
    ax.legend(loc="upper left", ncol=3, fontsize=8)
    axes[1].step(t, tr["inventaire"][m], where="post", color=COULEURS["as"])
    axes[1].axhline(0, color="black", lw=0.5)
    axes[1].set_ylabel("inventaire (lots)")
    axes[1].set_xlabel("minutes depuis 03h00 (New York)")
    pas = max(1, len(tr["temps"]) // 3000)  # sous-échantillonnage : 3 000 points suffisent à l'œil
    for s, trs in zip(strategies, trajectoires):
        axes[2].plot(trs["temps"][::pas] / 3600.0, trs["inventaire"][::pas], color=_couleur(s), lw=0.9, label=s.nom)
    axes[2].axhline(0, color="black", lw=0.5)
    axes[2].set_ylabel("inventaire (lots)")
    axes[2].set_xlabel("heures depuis 03h00 (New York)")
    axes[2].set_title("Même session, mêmes tirages : l'inventaire des stratégies comparées")
    axes[2].legend(fontsize=8, ncol=2)
    fig.tight_layout()
    _sauver(fig, dossier, "trajectoire_exemple.png")


def distributions_pnl(pnl_par_strategie, strategies, dossier):
    fig, axes = plt.subplots(2, 3, figsize=(14, 7), sharex=True, sharey=True)
    bornes = np.percentile(np.concatenate(list(pnl_par_strategie)), [0.5, 99.5])
    axes.ravel()[-1].axis("off")
    for ax, s, pnl in zip(axes.ravel(), strategies, pnl_par_strategie):
        ax.hist(pnl, bins=60, range=tuple(bornes), color=_couleur(s), alpha=0.85)
        ax.axvline(pnl.mean(), color="black", lw=1.2, label=f"moyenne {pnl.mean():.0f}")
        ax.axvline(0, color="red", lw=0.8, ls="--")
        ax.set_title(f"{s.nom} (écart-type {pnl.std(ddof=1):.0f})")
        ax.legend(fontsize=8)
    fig.supxlabel("PnL d'une session de 9 h (pips x lot ; 1 pip x lot = 100 USD)")
    fig.supylabel("nombre de sessions")
    fig.tight_layout()
    _sauver(fig, dossier, "distributions_pnl.png")


def decomposition_pnl(resumes, strategies, dossier):
    composantes = [("capture_spread", "capture de spread"), ("diffusion", "inventaire : diffusion du mid"),
                   ("dont_selection_adverse", "inventaire : sélection adverse"),
                   ("cout_liquidation", "coût de liquidation"), ("frais", "frais")]
    valeurs = []
    for r in resumes:
        d = r["decomposition_moyenne"]
        d = {**d, "diffusion": d["inventaire_total"] - d["dont_selection_adverse"]}
        valeurs.append([d[c] for c, _ in composantes])
    valeurs = np.array(valeurs)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    largeur = 0.16
    for j, (_, nom) in enumerate(composantes):
        ax.bar(np.arange(len(strategies)) + (j - 2) * largeur, valeurs[:, j], largeur, label=nom)
    ax.scatter(np.arange(len(strategies)), [r["pnl_moyen_pips_lot"] for r in resumes], marker="D", color="black", zorder=3, label="PnL total moyen")
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(np.arange(len(strategies)), [s.nom.replace(" ", chr(10), 1) for s in strategies], fontsize=8)
    ax.set_ylabel("pips x lot par session (moyenne)")
    ax.set_title("PnL moyen par session : la capture de spread domine, la sélection adverse en retire environ un cinquième")
    ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    _sauver(fig, dossier, "decomposition_pnl.png")


def _heatmap(ax, matrice, x_etiquettes, y_etiquettes, titre, xlabel, ylabel, fmt="{:.1f}", marque=None):
    vmax = max(abs(np.nanmin(matrice)), abs(np.nanmax(matrice)), 1e-9)
    cmap = plt.get_cmap("RdYlGn")
    norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
    ax.imshow(matrice, cmap=cmap, norm=norm, aspect="auto")
    for i in range(matrice.shape[0]):
        for j in range(matrice.shape[1]):
            r, g, b, _ = cmap(norm(matrice[i, j]))
            ax.text(j, i, fmt.format(matrice[i, j]), ha="center", va="center",
                    color="white" if 0.299 * r + 0.587 * g + 0.114 * b < 0.45 else "black", fontsize=9,
                    fontweight="bold" if marque == (i, j) else "normal")
    ax.set_xticks(range(len(x_etiquettes)), x_etiquettes)
    ax.set_yticks(range(len(y_etiquettes)), y_etiquettes)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(titre, fontsize=10)


def heatmap_simple(matrice, x_et, y_et, titre, xlabel, ylabel, dossier, nom, marque=None):
    fig, ax = plt.subplots(figsize=(7, 5))
    _heatmap(ax, matrice, x_et, y_et, titre, xlabel, ylabel, marque=marque)
    fig.tight_layout()
    _sauver(fig, dossier, nom)


def heatmaps_A_k(sharpe_ak, strategies, valeurs_A, valeurs_k, dossier):
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    axes.ravel()[-1].axis("off")
    for ax, j, s in zip(axes.ravel(), range(len(strategies)), strategies):
        _heatmap(ax, sharpe_ak[:, :, j], [f"{k:.1f}" for k in valeurs_k], [f"{a:.2f}" for a in valeurs_A],
                 s.nom, "k réel du marché (1/pip)", "A réel (exéc./s)", marque=(1, 1))
    fig.suptitle("Sharpe annualisé simulé : A et k réels différents des croyances (A=0,10 ; k=6, case en gras)")
    fig.tight_layout()
    _sauver(fig, dossier, "heatmap_A_k.png")


def sharpe_effondrement(p_vals, sharpe_p, L_vals_ms, sharpe_L, strategies, dossier):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
    for j, s in enumerate(strategies):
        axes[0].plot(p_vals, sharpe_p[:, j], marker="o", color=_couleur(s), label=s.nom)
        axes[1].plot(L_vals_ms, sharpe_L[:, j], marker="o", color=_couleur(s), label=s.nom)
    for ax in axes:
        ax.axhline(0, color="black", lw=0.6)
        ax.set_ylabel("Sharpe annualisé (simulation)")
    axes[0].set_xlabel("probabilité p de sélection adverse après une exécution")
    axes[1].set_xlabel("latence : délai entre deux mises à jour des cotes (ms)")
    axes[1].set_xscale("log")
    axes[0].set_title("Le Sharpe baisse quand le flux est plus informé")
    axes[1].set_title("... et s'effondre dès que les cotes sont périmées")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    _sauver(fig, dossier, "sharpe_effondrement.png")


def rejeu_pnl_cumule(dates, pnl_par_resolution, strategies, dossier):
    """PnL cumulé du rejeu (modèle de base) sous les deux lectures du cas « bid ET ask touchés »."""
    titres = {"adverse": "seul le côté perdant est exécuté (pessimiste)", "deux_cotes": "les deux côtés sont exécutés (optimiste)"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, (res, pnl_liste) in zip(axes, pnl_par_resolution.items()):
        for s, pnl in zip(strategies, pnl_liste):
            ax.plot(dates, np.cumsum(pnl), color=_couleur(s), label=f"{s.nom} ({pnl.sum():,.0f})".replace(",", " "))
        ax.axhline(0, color="black", lw=0.6)
        ax.set_title(titres[res], fontsize=10)
        ax.legend(fontsize=7, loc="lower left")
    axes[0].set_ylabel("PnL cumulé (pips x lot)")
    fig.suptitle("Rejeu sur barres 1 min EURUSD, VAL 2019-2022 (traversée >= 0,1 pip du MID, f = 0,5)")
    fig.autofmt_xdate()
    fig.tight_layout()
    _sauver(fig, dossier, "rejeu_val_pnl_cumule.png")


def rejeu_sensibilite(sharpe, fs, seuils, titre_strategie, dossier):
    fig, ax = plt.subplots(figsize=(7, 5))
    _heatmap(ax, sharpe, [f"{f:.2f}" for f in fs], [f"{x:+.1f}" for x in seuils],
             f"Rejeu VAL, {titre_strategie} : Sharpe annualisé (traversée < 0 : le mid n'a pas besoin d'atteindre la cote)",
             "probabilité de remplissage f", "traversée exigée (pips)")
    fig.tight_layout()
    _sauver(fig, dossier, "rejeu_sensibilite_f_seuil.png")


def sigma_par_heure(sigma_h, session, dossier):
    fig, ax = plt.subplots(figsize=(9, 4))
    couleurs = ["#1f77b4" if session[0] <= h < session[1] else "#b0b0b0" for h in range(24)]
    ax.bar(range(24), sigma_h, color=couleurs)
    ax.set_xlabel("heure de New York (HistData, heure d'été comprise)")
    ax.set_ylabel("sigma réalisé (pips / racine de s)")
    ax.set_title("Volatilité intrajournalière EURUSD, TRAIN 2010-2018 (session simulée en bleu)")
    fig.tight_layout()
    _sauver(fig, dossier, "sigma_par_heure.png")


def rejeu_modeles_fill(par_resolution, noms_modeles, strategies, dossier):
    """Figure centrale du rejeu : Sharpe de chaque stratégie selon le modèle de fill, sous les deux lectures « bid ET ask touchés ».

    par_resolution : {"adverse": (sharpes, bas, haut), "deux_cotes": (...)}, chaque élément [modèle][stratégie] ;
    barres d'erreur = IC95 bootstrap par blocs.
    """
    titres = {"adverse": "bid ET ask touchés : seul le côté perdant est exécuté (pessimiste)",
              "deux_cotes": "bid ET ask touchés : les deux côtés sont exécutés (optimiste)"}
    fig, axes = plt.subplots(1, 2, figsize=(15, 5.5), sharey=True)
    largeur = 0.8 / len(noms_modeles)
    for ax, (res, (sharpes, bas, haut)) in zip(axes, par_resolution.items()):
        for m, nom in enumerate(noms_modeles):
            x = np.arange(len(strategies)) + (m - (len(noms_modeles) - 1) / 2) * largeur
            sh = np.array(sharpes[m])
            ax.bar(x, sh, largeur, label=nom, alpha=0.45 + 0.25 * m, color="#4c72b0",
                   yerr=[sh - np.array(bas[m]), np.array(haut[m]) - sh], capsize=2)
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xticks(np.arange(len(strategies)), [s.nom.replace(" ", chr(10), 1) for s in strategies], fontsize=8)
        ax.set_title(titres[res], fontsize=10)
    axes[0].set_ylabel("Sharpe annualisé, rejeu VAL 2019-2022")
    fig.legend(*axes[0].get_legend_handles_labels(), title="modèle de fill", loc="lower center", ncol=3, fontsize=8)
    fig.suptitle("Le Sharpe d'un market maker rejoué sur barres dépend des conventions de fill (IC95 par blocs de 10 jours)")
    fig.tight_layout(rect=(0, 0.1, 1, 0.97))
    _sauver(fig, dossier, "rejeu_modeles_fill.png")


def markout_rejeu(markouts_par_resolution, strategies, dossier):
    """Markout moyen par exécution (pips) à +1, +5, +15 min. Négatif et plat, mais reproduit par une marche aléatoire sans dérive : c'est la convention de fill, pas la sélection adverse du marché réel."""
    titres = {"adverse": "seul le côté perdant est exécuté (convention punitive)",
              "deux_cotes": "les deux côtés sont exécutés"}
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    for ax, (res, markouts) in zip(axes, markouts_par_resolution.items()):
        horizons = list(markouts[0].keys())
        largeur = 0.8 / len(strategies)
        for j, (s, mk) in enumerate(zip(strategies, markouts)):
            x = np.arange(len(horizons)) + (j - (len(strategies) - 1) / 2) * largeur
            ax.bar(x, [mk[h]["moyenne_pips"] for h in horizons], largeur, color=_couleur(s), label=s.nom,
                   yerr=[1.96 * mk[h]["erreur_standard"] for h in horizons], capsize=2)
        ax.axhline(0, color="black", lw=0.6)
        ax.set_xticks(np.arange(len(horizons)), [f"+{h.replace('min', ' min')}" for h in horizons])
        ax.set_title(titres[res], fontsize=9)
    axes[0].set_ylabel("markout moyen par exécution (pips)")
    axes[1].legend(fontsize=7, loc="lower left")
    fig.suptitle("Markout du rejeu VAL (traversée 0,1 pip, f = 0,5) : négatif et plat, comme sur une marche aléatoire sans dérive (artefact de convention)")
    fig.tight_layout()
    _sauver(fig, dossier, "markout_rejeu.png")


def placebo_rejeu(comparaison, nom_ref, dossier):
    """Pour chaque lecture du cas « bid ET ask touchés » : Sharpe (haut) et PnL moyen par jour (bas), une valeur par graine."""
    titres = {"adverse": "côté perdant seul", "deux_cotes": "les deux côtés"}
    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    for col, (res, c) in enumerate(comparaison.items()):
        for ligne, nom_mesure in enumerate(("Sharpe annualisé", "PnL moyen par jour (pips x lot)")):
            ax = axes[ligne, col]
            ax.hist(c["placebo"][ligne], bins=12, color=COULEURS["placebo"], alpha=0.8, label="placebo (cotes aléatoires)")
            ax.hist(c["ref"][ligne], bins=12, color=COULEURS["as"], alpha=0.6, label=nom_ref)
            ax.set_xlabel(nom_mesure)
            ax.set_ylabel("graines")
            if ligne == 0:
                ax.set_title(titres[res], fontsize=10)
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("Placebo : une valeur par graine de tirages (file d'attente et largeur du placebo)")
    fig.tight_layout()
    _sauver(fig, dossier, "placebo_rejeu.png")
