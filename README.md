# Simulateur Monte Carlo — Coupe du Monde 2026

Simulateur Monte Carlo de la Coupe du Monde 2026 (48 équipes, format officiel FIFA)
basé sur les notes **Elo** transformées en buts attendus via un modèle de **Poisson**.
Le programme simule 50 000 tournois complets — de la phase de groupes à la finale —
puis agrège les probabilités de chaque sélection à chaque tour.

## Le modèle

**Monte Carlo Elo + Poisson.** Chaque match transforme l'écart Elo en supériorité de
buts attendue (1 but pour 300 points Elo), tire les scores selon deux lois de Poisson,
applique les règles FIFA (points, différence de buts, buts marqués) pour classer les
groupes, sélectionne les 8 meilleurs 3es, les affecte aux créneaux du Round of 32 selon
les contraintes d'éligibilité officielles (Annexe C), puis déroule toute la phase finale
(R32 → 8es → quarts → demies → finale au MetLife le 19 juillet).

- **Avantage hôte** : +60 Elo pour le Mexique, les États-Unis et le Canada.
- **Données** (état au 6 juin 2026) : composition des 12 groupes (tirage FIFA du 5 déc.
  2025 + barrages mars/avril 2026), notes Elo (eloratings.net pour le top 12, Elo de
  janvier pour le 2e rideau, estimations ancrées sur le classement FIFA pour le reste),
  cotes de marché FanDuel/BetMGM comme étalon de comparaison.

### Limites assumées
Le modèle ignore blessures, forme du jour, compositions, météo et altitude de Mexico,
dynamique d'effectif. Les notes hors top 20 sont estimées. Le réglage du diviseur (300)
gouverne le taux de surprises.

## Paramètres modifiables

En tête du fichier [`cdm2026_sim.py`](cdm2026_sim.py) :

| Paramètre    | Valeur | Rôle                                                   |
|--------------|-------:|--------------------------------------------------------|
| `N_SIMS`     | 50 000 | Nombre de tournois simulés                             |
| `DIV_GOALS`  |    300 | Points Elo par but de « suprématie »                   |
| `MU_TOTAL`   |   2.70 | Buts attendus par match (moyenne internationale)       |
| `HOST_BONUS` |     60 | Bonus Elo appliqué aux pays hôtes                      |
| `SEED`       |   ...  | Graine aléatoire (reproductibilité)                    |

## Installation & exécution

```bash
pip install -r requirements.txt
python cdm2026_sim.py
```

Le script affiche le classement des 24 meilleures équipes (probabilités de titre,
finale, demie, quart, R16, R32) face aux cotes de marché, des contrôles de cohérence,
et écrit le fichier `cdm2026_probabilities.csv` (8 indicateurs pour les 48 équipes).

## Principaux résultats (50 000 simulations)

| # | Équipe    | Gr | Titre | Finale | Demie | Qualif. R32 |
|---|-----------|----|------:|-------:|------:|------------:|
| 1 | Espagne   | H  | 19,0  | 28,4   | 40,2  | 97,9        |
| 2 | Argentine | J  | 14,1  | 22,6   | 34,0  | 96,7        |
| 3 | France    | I  | 10,2  | 17,4   | 29,9  | 92,0        |
| 4 | Angleterre| L  | 6,8   | 12,8   | 22,7  | 92,8        |
| 5 | Brésil    | C  | 5,0   | 10,0   | 19,6  | 91,6        |

À elles trois, Espagne, Argentine et France concentrent ~43 % des titres simulés.

> **Note structurelle** : les vainqueurs des groupes D, E, F, G, H, I tombent tous dans
> la même moitié de tableau. Espagne et France ne pourraient donc se croiser qu'en
> demi-finale — ce qui pénalise la France dans le modèle par rapport à sa cote de marché.

## Application web interactive (`index.html`)

En plus du script Python, le dépôt contient une **web-app** qui rejoue la même
simulation Monte Carlo directement dans le navigateur (paramètres ajustables,
contraintes de résultats, comparaison au marché). Elle est publiée via GitHub Pages :

👉 **https://stephanelanglet-angle.github.io/cdm2026-simulateur/**

**Saisie des résultats réels.** Pour chaque match de poule, on peut « verrouiller »
le résultat (1 / N / 2) ; la simulation se recalcule en conditionnant sur ce résultat.
Les verrous sont conservés localement (`localStorage`) et **synchronisés entre appareils**
(iPhone / PC) via Firebase Realtime Database : un même *code de synchro* saisi sur
plusieurs appareils partage les résultats en temps réel (bouton ☁️).

## Avertissement

Modèle statistique à but exploratoire/pédagogique. Les probabilités reflètent des
hypothèses (Elo, Poisson, diviseur) et non une prédiction certaine. Aucun lien avec
un quelconque conseil de pari.
