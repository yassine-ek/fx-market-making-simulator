# `notebooks/` : le carnet exécuté

Un carnet Jupyter avec ses sorties (lisible sur GitHub sans rien installer). Il est généré par un script, pas écrit à la main.

| Fichier | Ce qu'il montre |
|---|---|
| `visite_guidee.ipynb` | Visite pas à pas, chaque bloc suivant le fil intuition → formule → attente → code → lecture : le problème du market maker, le prix de réservation d'Avellaneda-Stoikov, les quatre façons de gérer l'inventaire, une session simulée, le Monte Carlo, pourquoi le Sharpe de simulation n'est pas un Sharpe de marché (sélection adverse, latence), le rejeu sur EURUSD 1 minute réel et le markout, puis la conclusion. Généré par `scripts/construire_notebook.py`. |

Réexécuter : `python scripts/construire_notebook.py && python -m jupyter nbconvert --to notebook --execute --inplace notebooks/visite_guidee.ipynb` (données HistData et `HISTDATA_DIR` requis, voir le README principal ; nbformat, nbconvert et ipykernel à installer).
