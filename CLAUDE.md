# CLAUDE.md — Simulateur Coupe du Monde 2026

## Quoi
Simulateur Monte Carlo de la CDM 2026 + stratège de pronos, déployé sur GitHub Pages.
Repo : `stephanelanglet-Angle/cdm2026-simulateur` → https://stephanelanglet-angle.github.io/cdm2026-simulateur/

## Fichiers
- `cdm2026_sim.py` — moteur Monte Carlo Elo+Poisson de référence (lignes 23-26 = les 3 params).
- `index.html` — « la régie » : web-app qui rejoue la même simulation côté navigateur. **Source unique** des paramètres et de l'Elo.
- `castrol.html` — stratège de pronos pour le concours « Castrol Legends » (9 joueurs). Lit les params/Elo de la régie ; même origine → partage le localStorage.
- `scripts/update-elo.mjs` + `.github/workflows/update-elo.yml` — maj Elo quotidienne depuis eloratings.net → `elo.json` (racine).
- `elo.json` — `{_source, _updated, elo:{48 équipes}}`, lu par les 2 pages au chargement.
- `scripts/update-fairplay.mjs` + `update-fairplay.yml` — **toutes les 2h** : table « Discipline » de Wikipédia (1 page/groupe) → `fairplay.json` `{points:{équipe EN: score Art.13 ≤ 0}}`. Critère de fair-play du départage.
- `scripts/update-fifaranking.mjs` + `update-fifaranking.yml` — **quotidien** : API officielle `inside.fifa.com/api/ranking-overview` → `fifa.json` `{fifa:{équipe FR:{rank,points}}}`. Critère ultime de départage.
- `thirds.json` + `scripts/build-thirds.mjs` — table **OFFICIELLE FIFA des 495 combinaisons** d'affectation des 8 meilleurs 3es au R32 (Annexe C / Wikipédia, **statique**, pas de cron). `castrol.html` la lit dans `THIRDS_TABLE` ; repli sur le couplage Kuhn d'`assignThirds` si absente.

## Modèle (identique dans les 3 livrables)
- `sup = (eloA - eloB) / DIV_GOALS` ; `λ = [(MU_TOTAL + sup)/2, (MU_TOTAL - sup)/2]` ; buts ~ Poisson(λ).
- 3 paramètres réglables : `HOST_BONUS` (+60 Elo aux hôtes MEX/USA/CAN), `DIV_GOALS` (300), `MU_TOTAL` (2.70).
- `DIV_GOALS=300` = Elo par but de supériorité (≠ le 400 de la proba de victoire).
- Barème Castrol : **4/3/2/0** (exact / écart / résultat / faux). **Tous les bonus = 4 pts** (Tor / 4 DF / 12 vainqueurs de groupe ordre A,B,C,D,F,G,H,I,J,K,L,E / champion).

## Stratégie de reco (Castrol)
- Objectif = **gagner le concours** = maximiser **P(finir 1er)**, pas marquer dans l'absolu. `winSim` suit `winP` (1er), `podP` (podium), `overP` (doubler le leader), `gap` (écart final moyen). RNG reseedable (`reseed(SIM_SEED)`) ⇒ comparaisons **appariées** (mêmes tournois simulés, seule la stratégie change).
- **`winSim(…, meStrat)`** : le « futur moi » joue **EV** (`meStrat=0`) ou prend une **dose de variance** `catchUpPick(G, prono_leader, dose)` (`meStrat>0`) sur tous les matchs à venir.
- **DÉCOUVERTE CLÉ (mesurée le 18/06, à 17 pts du leader)** : la dose de variance du « futur moi » a un **point idéal ~0,1** qui **maximise P(1er)** — de **~0 % en EV pur à ~3-4 %** (podium ×4) ! **Trop** de variance (≥0,3) **coule** (l'espérance s'effondre, on finit dernier). ⚠️ L'ancienne conclusion « jouer EV partout / la variance ne paie pas » était une **SUR-CORRECTION** (elle ne testait que l'extrême). Concrètement la bonne dose = « favori en **clean sheet** (2-0) » plutôt que le 2-1 de consensus.
- **`runWin` = « Mode Gagner »** (défaut `braquet='cible'`) : balaie `WIN_DOSES=[0,0.08,0.12,0.18,0.28]` (appariés) et retient la dose qui **maximise P(1er)** ; revient à **0/EV** quand on mène ou que la variance ne paie pas (auto-régulé). Affiche P(1er)/podium/doubler vs safe + le sweep + le « pourquoi ». Niveaux manuels = doses fixes **0/0,1/0,2/0,4** (Prudent EV → All-in).
- `catchUpPick(G, prono_leader, dose)` : maximise `E[D] + λ·SD[D]` (D = mes points − ceux du leader) sur des scores **plausibles** (top-10 probables, sinon « all-in » choisit des scores absurdes type 0-0 pour un gros favori).
- **Audit (vérifié)** : jouer l'optimal du modèle plutôt que l'instinct vaut **~+7 pts** (fuite à colmater : ne pas freelancer des 1-1). Mais même l'optimal reste **~10 pts sous un leader fort** qui plante des **exacts** ⇒ la remontée passe par la **variance dosée** + les **bonus** (4 pts pièce, son champion Portugal ≠ France de Martin).
- Navigation : onglets réciproques `.pgnav` (Régie ↔ Castrol) en haut des deux pages.

## Règles de travail (IMPORTANT)
- **Ne jamais inventer de scores.** La CDM 2026 est postérieure au cutoff → toujours vérifier sur le web.
- **Ne pas modifier les 3 params à la place de l'utilisateur** sans accord — il calibre à la main au fil du tournoi.
- Vérifier les changements observables via l'aperçu navigateur (`mcp__Claude_Preview__*`), pas en demandant à l'utilisateur de tester.
- Probas 1N2 doivent rester **identiques** entre régie et Castrol (même params, même Elo, affichage 1 décimale des deux côtés).

## Gotchas
- **Scotland = code `SQ`** dans eloratings.net (`SC` = Seychelles).
- **Cron GitHub Actions** : ne pas planifier à l'heure ronde (`0 H * * *`) — créneau congestionné, runs planifiés retardés/abandonnés. Update-elo tourne à `'23 5,13,21 * * *'`. Le script écrit `_updated` à la date du jour à chaque run ⇒ un run réussi committe toujours (sauf si scores identiques ET même date). Déclencher à la main : onglet Actions → Run workflow (ou lancer `node scripts/update-elo.mjs` en local puis commit).
- Dans le JS des pages, `$ = getElementById` → passer un **id nu** (`$('foo')`), jamais `$('#foo')`.
- Persistance Castrol versionnée : clé `castrol_legends_state_v2`, `SCHEMA=2`. Les données d'un ancien schéma (local/cloud) sont **ignorées** (sinon écrasement des résultats + boucle de rendu).
- Saisie des pronos : `detailBusy()` (garde 4 s + focus) empêche un push de synchro d'un autre appareil de ré-rendre `renderDetail` et d'effacer la frappe en cours. Ne pas reconstruire le panneau pendant la saisie.
- L'Action GitHub exige « Read and write permissions » (Settings → Actions) — déjà activé.
- Bracket KO (matchs 73-104) : la sim les **projette**. Carte « Groupes & tableau final » de Castrol (`renderKO`/`koTab`) les **affiche** désormais (lecture seule) : `renderGroupStandings` (12 classements live, ordre exact Art.13 via `fifaRankGroup` quand le groupe est terminé, sinon tri pts/diff/buts) + `renderBracket` = **projection CONTINUE** : `bracketData` classe chaque poule avec son ordre **provisoire** (pas besoin qu'elle soit finie) → remplit le R32, puis projette les **vainqueurs KO = favori Elo** (`effElo`) jusqu'au champion. Style : **gras** = qualifié confirmé (poule terminée pour 1er/2e ; toutes les poules finies pour les 3es), **italique** = provisoire. Toujours **pas saisissables** (pas de saisie des scores KO).
- **Départage des groupes (Art.13 FIFA 2026)** : `fifaRankGroup()` (castrol) = pts → confrontation directe (a/b/c, **récursive** sur le sous-groupe à égalité) → diff générale → buts généraux → **fair-play** (`fairScore`/`fairplay.json`) → **classement FIFA** (`fifaScore`/`fifa.json`) → Elo (ultime secours). Aucun tirage au sort, 100 % déterministe. Même chaîne pour les 8 meilleurs 3es (`best8`). Helpers globaux `fairScore(tm)` / `fifaScore(tm)`.
- **Codes FIFA ≠ eloratings** : `update-fifaranking.mjs` mappe nos 48 noms FR → code FIFA 3 lettres maison (GER, NED, POR, CRO, SUI, USA, SCO, KSA, RSA, CIV, CUW, COD…), ≠ codes eloratings (DE, NL, US, SQ…). Garde-fou : points < 1100 ⇒ mauvais code.
- **Fair-play Wikipédia** (`update-fairplay.mjs`) : la colonne « Score » des pages `2026_FIFA_World_Cup_Group_X` est **déjà** au barème Art.13 (≤ 0). Pièges de parsing : titre « national **soccer** team » (USA/RSA) ET « football team » ; « **men's** » dans le titre (USA/Canada) ; cellule Score = `<th>` pas `<td>` (prendre la **dernière** cellule td|th) ; tiret unicode U+2212. `fairplay.json` keyé EN → l'app reconvertit via `EN2FR`. Équipe absente = 0 carton (meilleur).
- **Table des 3es (FIFA 2026)** : `TS_MATCH=[74,77,79,80,81,82,85,87]` + `TS_ELIG` conformes à la table officielle (un 3e affronte toujours un 1er). L'affectation **exacte** des 495 combinaisons (Annexe C) est embarquée dans `thirds.json` : clé = 8 lettres triées (groupes qualifiés), valeur = 8 chars = le 3e par match dans l'ordre `TS_MATCH`. `winSim` lit `THIRDS_TABLE[combo]` ; `assignThirds` (couplage Kuhn) ne sert plus qu'en **repli**. `scripts/build-thirds.mjs` régénère le fichier depuis `Template:2026_FIFA_World_Cup_third-place_table` ; invariants vérifiés (495 combos uniques, 0 non-éligible, 0 auto-groupe, TS_ELIG dérivé conforme).

## Calibrage auto des 3 paramètres
- **Castrol** ré-estime `hostBonus/divGoals/muTotal` depuis les **scores observés** par MAP : NLL de Poisson + pénalité gaussienne ancrée sur 60/300/2,70 (peu de matchs ⇒ proche des défauts ; au fil du tournoi ⇒ piloté par les données). Fonction `calibrate()` + carte « Calibrage tournoi » (suggestion + toggle auto).
- Publie dans la **clé localStorage dédiée `cdm2026_calib`** `{auto,hostBonus,divGoals,muTotal,n,obsMu}`. La **régie consomme cette clé en lecture seule** (applique si `auto`, grise les curseurs, badge « calé sur le tournoi » / « suggère… »). Castrol = autorité du calibrage ; pas d'inversion de la source des paramètres.
- Le scoring se cale uniquement sur les scores joués (`m.res`, noms FR via `EN2FR`). Bonus hôte = 3 équipes ⇒ bouge lentement (honnête).

## Sync
- **Firebase Realtime Database** (projet `cdm2026-sync`, config publique dans `index.html`), chemin `rooms/$code` (accès si `$code.length >= 6`). Même « code de synchro » sur chaque appareil = résultats partagés iPhone/PC.
- Régie ↔ Castrol : localStorage même origine + resync sur load/focus/visibilitychange/événement `storage`.
- `calibAuto` est **local à l'appareil** (stocké dans `cdm2026_calib`, pas synchronisé via Firebase).

## Commandes
- Serveur local : `python -m http.server 8765` (cf. `.claude/launch.json`).
- Déploiement : push sur `main` → GitHub Pages (~60 s de latence). Recharger avec **Ctrl+Maj+R**.

## Reste à faire
- UI de saisie des matchs à élimination directe (n°73-104), quand le bracket se matérialise après les poules.
- Couche d'ajustement Elo manuel (blessures/météo), par-dessus l'auto eloratings.
- ~~Niveau d'audace réglable~~ → fait (braquet, cf. « Stratégie de reco »).
- Calibrage auto : `calibAuto` par défaut OFF (mode suggestion) ; l'utilisateur active l'auto dans Castrol. Limite v1 : si la régie sauvegarde pendant que l'auto est ON, les params calibrés deviennent le « manuel » persisté (pas de baseline manuel séparé). Curseurs régie : pas grossiers (hôte ±10, div ±10, μ ±0,05) ⇒ le thumb se cale sur le cran, le libellé porte la valeur exacte.
