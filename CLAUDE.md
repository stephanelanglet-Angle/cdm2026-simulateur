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

## Modèle (identique dans les 3 livrables)
- `sup = (eloA - eloB) / DIV_GOALS` ; `λ = [(MU_TOTAL + sup)/2, (MU_TOTAL - sup)/2]` ; buts ~ Poisson(λ).
- 3 paramètres réglables : `HOST_BONUS` (+60 Elo aux hôtes MEX/USA/CAN), `DIV_GOALS` (300), `MU_TOTAL` (2.70).
- `DIV_GOALS=300` = Elo par but de supériorité (≠ le 400 de la proba de victoire).
- Barème Castrol : **4/3/2/0** (exact / écart / résultat / faux). **Tous les bonus = 4 pts** (Tor / 4 DF / 12 vainqueurs de groupe ordre A,B,C,D,F,G,H,I,J,K,L,E / champion).

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
- Bracket KO (matchs 73-104) : la sim les **projette** mais ils ne sont pas encore saisissables dans l'UI.

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
- Optionnel : niveau d'audace réglable.
- Calibrage auto : `calibAuto` par défaut OFF (mode suggestion) ; l'utilisateur active l'auto dans Castrol. Limite v1 : si la régie sauvegarde pendant que l'auto est ON, les params calibrés deviennent le « manuel » persisté (pas de baseline manuel séparé). Curseurs régie : pas grossiers (hôte ±10, div ±10, μ ±0,05) ⇒ le thumb se cale sur le cran, le libellé porte la valeur exacte.
