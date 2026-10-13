import numpy as np
import pytest

from mm.donnees import dossier_donnees
from mm.modeles import Strategie, jeu_strategies_base, strategie_placebo
from mm.rejeu_reel import HORIZONS_MARKOUT, N_BARRES, construire_jours, jours_marche_aleatoire, rejouer, resume_markout
from mm.simulateur import (Marche, O_CAPTURE, O_FRAIS, O_INVENTAIRE, O_LIQUIDATION, O_NEXEC, O_PNL, O_PNL_CASH,
                           O_QFINAL, O_QMAX)

P0 = 11000.0  # prix de départ en pips
MARCHE = Marche(sigma=0.33, A=0.1, k=6.0, p_adverse=0.0, alpha=0.3, demi_spread_liq=0.1, frais=0.0)


def naif(demi=0.2, Q=20):
    return Strategie("naif", "naif", 0.0, sigma=0.33, k=6.0, A=0.1, demi_naif=demi, cap=0.1, Q=Q)


def jours_plats(n_jours=1):
    """Barres parfaitement plates : aucune exécution possible tant qu'on ne les modifie pas."""
    c = np.full((n_jours, N_BARRES), P0)
    return {"dates": np.arange(n_jours), "O": c.copy(), "H": c.copy(), "L": c.copy(), "C": c.copy(),
            "valide": np.ones((n_jours, N_BARRES), bool)}


def jours_aleatoires(n_jours=6, graine=0):
    rng = np.random.default_rng(graine)
    close = P0 + np.cumsum(rng.standard_normal((n_jours, N_BARRES)) * 2.5, axis=1)
    haut = close + np.abs(rng.standard_normal(close.shape)) * 1.5
    bas = close - np.abs(rng.standard_normal(close.shape)) * 1.5
    ouv = np.roll(close, 1, axis=1)
    return {"dates": np.arange(n_jours), "O": ouv, "H": np.maximum(haut, ouv), "L": np.minimum(bas, ouv), "C": close,
            "valide": np.ones(close.shape, bool)}


def test_rejeu_sans_look_ahead_les_cotes_ne_dependent_que_du_passe():
    jours = jours_aleatoires()
    as_ = jeu_strategies_base(0.33, 0.1, 6.0, 20, 32400.0)[1]
    _, _, bid, ask = rejouer(jours, as_, MARCHE, 0.0, 1.0, detail=True)
    k = 200
    futur = {c: v.copy() if c != "dates" and c != "valide" else v for c, v in jours.items()}
    rng = np.random.default_rng(99)
    for c in "OHLC":  # on massacre toutes les barres à partir de k : la cote de la barre k n'utilise que la barre k-1
        futur[c][:, k:] = P0 + 50 * rng.standard_normal(futur[c][:, k:].shape)
    _, _, bid2, ask2 = rejouer(futur, as_, MARCHE, 0.0, 1.0, detail=True)
    assert np.array_equal(bid[:, 1:k + 1], bid2[:, 1:k + 1]) and np.array_equal(ask[:, 1:k + 1], ask2[:, 1:k + 1])
    assert not np.array_equal(bid[:, k + 1:], bid2[:, k + 1:])  # non vacuité : après k, ça change bien


def plat_avec_barre(i, haut=None, bas=None, close=None):
    """Journée plate sauf la barre i ; si `close` est donné, le prix reste ensuite plat à ce niveau."""
    j = jours_plats()
    if haut is not None:
        j["H"][0, i] = haut
    if bas is not None:
        j["L"][0, i] = bas
    if close is not None:
        j["C"][0, i:] = close
        for c in "OHL":
            j[c][0, i + 1:] = close
    return j


def n_exec(jours, seuil, f=1.0, deux_cotes=False):
    return rejouer(jours, naif(0.2), MARCHE, seuil, f, deux_cotes=deux_cotes)[0, O_NEXEC]


def test_toucher_ne_suffit_pas_il_faut_traverser_de_0_1_pip():
    bas_025 = plat_avec_barre(5, bas=P0 - 0.25)   # cote à P0-0.2 : traversée de 0,05 pip seulement
    bas_035 = plat_avec_barre(5, bas=P0 - 0.35)   # traversée de 0,15 pip
    assert n_exec(bas_025, seuil=0.1) == 0 and n_exec(bas_035, seuil=0.1) == 1
    assert n_exec(bas_025, seuil=0.0) == 1  # le modèle « toucher suffit » exécute, lui


def test_probabilite_de_file_f():
    j = plat_avec_barre(5, bas=P0 - 0.35)
    assert n_exec(j, 0.1, f=0.0) == 0 and n_exec(j, 0.1, f=1.0) == 1
    jours = jours_aleatoires(40)
    pleins, moitie = (rejouer(jours, naif(), MARCHE, 0.0, f)[:, O_NEXEC].sum() for f in (1.0, 0.5))
    assert moitie == pytest.approx(0.5 * pleins, rel=0.1)


def test_bid_et_ask_touches_ordre_defavorable_le_cote_perdant_dabord():
    j = plat_avec_barre(5, haut=P0 + 0.5, bas=P0 - 0.5, close=P0 - 0.4)  # la barre finit en baisse : le bid (achat) perd
    adverse = rejouer(j, naif(0.2), MARCHE, 0.1, 1.0, deux_cotes=False)[0]
    assert adverse[O_NEXEC] == 1 and adverse[O_CAPTURE] == pytest.approx(0.2)
    assert adverse[O_QFINAL] == 1 and adverse[O_INVENTAIRE] == pytest.approx(-0.4)  # 1 lot long, le mid finit 0,4 pip plus bas
    deux = rejouer(j, naif(0.2), MARCHE, 0.1, 1.0, deux_cotes=True)[0]
    assert deux[O_NEXEC] == 2 and deux[O_QFINAL] == 0 and deux[O_CAPTURE] == pytest.approx(0.4)
    haussier = plat_avec_barre(5, haut=P0 + 0.5, bas=P0 - 0.5, close=P0 + 0.4)  # fin en hausse : l'ask (vente) perd
    assert rejouer(haussier, naif(0.2), MARCHE, 0.1, 1.0)[0, O_QFINAL] == -1


def test_inventaire_borne_dans_le_rejeu():
    res = rejouer(jours_aleatoires(10), naif(0.05, Q=3), MARCHE, 0.0, 1.0)
    assert res[:, O_QMAX].max() == 3


def test_identite_comptable_rejeu_a_1e_9():
    jours = jours_aleatoires(10)
    strategies = jeu_strategies_base(0.33, 0.1, 6.0, 20, 32400.0)
    strategies.append(strategie_placebo(strategies[1], 0.17))
    marche = Marche(sigma=0.33, A=0.1, k=6.0, p_adverse=0.0, alpha=0.3, demi_spread_liq=0.1, frais=0.01)
    for s in strategies:
        for seuil, f, deux in [(0.0, 1.0, False), (0.1, 0.5, True), (0.1, 0.5, False)]:
            r = rejouer(jours, s, marche, seuil, f, deux_cotes=deux)
            somme = r[:, O_CAPTURE] + r[:, O_INVENTAIRE] - r[:, O_LIQUIDATION] - r[:, O_FRAIS]
            assert np.abs(r[:, O_PNL] - somme).max() < 1e-9
            assert np.abs(r[:, O_PNL] - r[:, O_PNL_CASH]).max() < 1e-9


def test_markout_calcule_a_la_main():
    j = plat_avec_barre(5, bas=P0 - 0.35)
    for c in "OHLC":  # le mid reste 1 pip plus bas dès la barre suivante
        j[c][0, 6:] = P0 - 1.0
    _, markout, _, _ = rejouer(j, naif(0.2, Q=1), MARCHE, 0.1, 1.0, detail=True)  # Q=1 : un seul achat, pas de réachat à la baisse
    mk = resume_markout(markout)
    assert mk["1min"]["n_executions"] == 1 and mk["1min"]["moyenne_pips"] == pytest.approx(-1.0 + 0.2)  # achat à P0-0.2
    assert list(mk) == [f"{h}min" for h in HORIZONS_MARKOUT]


def test_controle_marche_aleatoire_le_markout_negatif_vient_de_la_convention_de_fill():
    """Une marche aléatoire SANS dérive ni sélection adverse donne déjà un markout négatif et plat de +1 à +15 min.

    La traversée exigée (0,1 pip) et le dépassement du prix à l'intérieur d'une barre suffisent : le markout du rejeu
    n'est donc pas, en soi, une mesure de la sélection adverse du marché réel (régression : le README le présentait ainsi).
    """
    j = jours_marche_aleatoire(40, 1.9, graine=3)
    _, markout, _, _ = rejouer(j, naif(0.17), MARCHE, 0.1, 0.5, deux_cotes=True, detail=True)
    m = resume_markout(markout)
    assert all(m[k]["moyenne_pips"] < -0.15 for k in m), m
    assert abs(m["1min"]["moyenne_pips"] - m["15min"]["moyenne_pips"]) < 0.1  # plat : rien ne « suit » après l'exécution


def test_reproductibilite_par_graine():
    jours = jours_aleatoires()
    a, b, c = (rejouer(jours, naif(), MARCHE, 0.1, 0.5, graine=g)[:, O_PNL] for g in (1, 1, 2))
    assert np.array_equal(a, b) and not np.array_equal(a, c)


def _donnees_presentes():
    return (dossier_donnees() / "EURUSD_2019.zip").exists()


MOTIF = "données HistData absentes : définir HISTDATA_DIR (voir README, section Reproduire)"


@pytest.mark.skipif(not _donnees_presentes(), reason=MOTIF)
def test_donnees_reelles_2019_identite_et_cotes_sur_prix_reels():
    jours = construire_jours([2019], 0.1)
    assert jours["C"].shape[0] > 200 and jours["C"].shape[1] == N_BARRES and jours["C"].mean() > 1e4  # pips
    r, _, bid, _ = rejouer(jours, naif(0.2), MARCHE, 0.1, 0.5, detail=True)
    assert np.abs(r[:, O_PNL] - r[:, O_PNL_CASH]).max() < 1e-9
    assert np.nanmax(np.abs(bid[:, 1:] - jours["C"][:, :-1] + 0.2)) < 1e-6  # cote = close précédent - 0,2 pip, en prix d'origine


@pytest.mark.skipif(not _donnees_presentes(), reason=MOTIF)
def test_fuseau_donnees_a_l_heure_de_new_york_semaine_rouverte_a_17h_en_juillet():
    """Régression : les zips HistData sont à l'heure LOCALE de New York (pas en EST fixe UTC-5).

    Réouverture du dimanche à 17h00 en juillet comme en janvier (en UTC-5 fixe : 16h00 en juillet) ; la session 03h-12h
    des données est donc alignée sur 08h-17h Londres toute l'année.
    """
    from mm.donnees import charger_annee
    barres = charger_annee(2019)
    for d in ("2019-07-07", "2019-07-14", "2019-07-21", "2019-07-28", "2019-01-13", "2019-01-20"):
        jour = barres.loc[d]
        assert (jour.index[0].hour, jour.index[0].minute) == (17, 0), d
