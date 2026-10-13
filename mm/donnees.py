"""Lecture des barres 1-minute EURUSD HistData (BID, heure LOCALE de New York, heure d'été comprise).

FUSEAU : malgré la documentation HistData (« EST sans heure d'été »), les fichiers sont à l'heure de New York avec
changement d'heure : le NFP (8h30 ET) fait le pic de la journée à 8h30 l'été comme l'hiver, la semaine rouvre le
dimanche à 17h00 et ferme le vendredi à 16h59 en toute saison. La session 03h-12h correspond donc à 08h-17h Londres
toute l'année (sauf ~3 semaines où les passages à l'heure d'été US et européen sont décalés).

Split temporel imposé : TRAIN <= 2018 (calibration), VAL 2019-2022 (évaluation).
Le TEST (2023+) est scellé PAR CONSTRUCTION : `charger_annee` refuse de le lire.
"""
import os
import zipfile
from pathlib import Path

import pandas as pd

ANNEE_TRAIN_FIN = 2018
ANNEES_VAL = range(2019, 2023)
ANNEE_TEST_DEBUT = 2023
PIP = 1e-4


RACINE_PROJET = Path(__file__).resolve().parents[1]


def dossier_donnees():
    """<HISTDATA_DIR>/histdata_raw/EURUSD, avec HISTDATA_DIR = variable d'environnement, sinon <projet>/data/histdata (non versionné).

    Fichiers attendus : EURUSD_<année>.zip (minutes HistData, BID). Les données ne sont jamais redistribuées.
    """
    racine = Path(os.environ.get("HISTDATA_DIR") or RACINE_PROJET / "data" / "histdata")
    return racine / "histdata_raw" / "EURUSD"


def charger_annee(annee):
    """Barres 1 min d'une année : colonnes open/high/low/close en PIPS (prix * 1e4), index = heure de New York (voir l'en-tête)."""
    if annee >= ANNEE_TEST_DEBUT:
        raise PermissionError(f"{annee} appartient au TEST (2023+), scellé : lecture interdite.")
    chemin = dossier_donnees() / f"EURUSD_{annee}.zip"
    with zipfile.ZipFile(chemin) as z:
        nom = next(n for n in z.namelist() if n.endswith(".csv"))  # le zip contient aussi un .txt de description
        brut = pd.read_csv(z.open(nom), header=None, names=["d", "t", "open", "high", "low", "close", "vol"],
                           usecols=range(6))
    brut.index = pd.to_datetime(brut.pop("d") + " " + brut.pop("t"), format="%Y.%m.%d %H:%M")
    return brut / PIP
