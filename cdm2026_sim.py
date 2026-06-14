# -*- coding: utf-8 -*-
"""
Simulateur Monte Carlo - Coupe du monde 2026 (48 equipes)
=========================================================
Pipeline : donnees (Elo + format officiel) -> modele de match (Elo -> Poisson)
-> simulation de N tournois complets -> probabilites par equipe.

Sources des donnees (collectees le 6 juin 2026) :
- Composition des 12 groupes : tirage FIFA du 5 dec. 2025 + barrages mars/avril 2026.
- Notes Elo : eloratings.net via footballratings.org (6 juin 2026) pour le top 12 ;
  Elo de janvier 2026 pour le 2e rideau ; estimations ancrees sur le classement FIFA
  (avril 2026) + Elo historique pour les nations hors top 20.
- Arbre de bracket (R32 -> finale) : calendrier officiel FIFA (MLS/NBC/Bleacher Report).

Modele assume et documente (parametres en tete de fichier, faciles a modifier).
"""

import numpy as np

# ----------------------------------------------------------------------------
# PARAMETRES DU MODELE (modifiables)
# ----------------------------------------------------------------------------
N_SIMS      = 50_000     # nombre de tournois simules
DIV_GOALS   = 300.0      # Elo par but de "supremacy" (300 -> +1 but pour +300 Elo)
MU_TOTAL    = 2.70       # buts attendus par match (moyenne internationale)
HOST_BONUS  = 60.0       # bonus Elo applique aux pays hotes sur tous leurs matchs
SEED        = 20260606
rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------
# DONNEES : 48 equipes, 12 groupes (A..L), notes Elo
# elo "mesure" = top 20 (eloratings) ; "estime" = ancre sur classement FIFA
# ----------------------------------------------------------------------------
GROUPS = {
    'A': [('Mexique',1800),('Coree du Sud',1760),('Afrique du Sud',1640),('Tchequie',1780)],
    'B': [('Canada',1750),('Suisse',1897),('Qatar',1675),('Bosnie',1690)],
    'C': [('Bresil',1988),('Maroc',1845),('Ecosse',1770),('Haiti',1560)],
    'D': [('Etats-Unis',1790),('Paraguay',1730),('Australie',1715),('Turquie',1880)],
    'E': [('Allemagne',1925),('Equateur',1935),('Cote d\'Ivoire',1745),('Curacao',1565)],
    'F': [('Pays-Bas',1944),('Japon',1879),('Suede',1790),('Tunisie',1685)],
    'G': [('Belgique',1849),('Iran',1800),('Egypte',1660),('Nouvelle-Zelande',1505)],
    'H': [('Espagne',2155),('Uruguay',1890),('Arabie saoudite',1635),('Cap-Vert',1615)],
    'I': [('France',2062),('Senegal',1869),('Norvege',1917),('Irak',1600)],
    'J': [('Argentine',2113),('Autriche',1785),('Algerie',1760),('Jordanie',1605)],
    'K': [('Portugal',1984),('Colombie',1977),('Ouzbekistan',1680),('RD Congo',1680)],
    'L': [('Angleterre',2020),('Croatie',1908),('Panama',1650),('Ghana',1635)],
}
HOSTS = {'Mexique','Etats-Unis','Canada'}

# ---- index global des equipes ----------------------------------------------
GROUP_LETTERS = list(GROUPS.keys())                 # A..L
teams, elo = [], []
group_of = []                                       # lettre de groupe par team id
gidx_of  = {}                                       # (lettre) -> [4 team ids]
for gi, L in enumerate(GROUP_LETTERS):
    ids = []
    for name, e in GROUPS[L]:
        tid = len(teams)
        teams.append(name)
        eff = e + (HOST_BONUS if name in HOSTS else 0.0)   # bonus hote integre
        elo.append(eff)
        group_of.append(L)
        ids.append(tid)
    gidx_of[L] = ids
elo = np.array(elo, dtype=np.float64)
NT = len(teams)
team_id = {n:i for i,n in enumerate(teams)}
assert NT == 48

# ----------------------------------------------------------------------------
# MODELE DE MATCH
# ----------------------------------------------------------------------------
def expect(dr):
    """Esperance de resultat (echelle 0-1) facon Elo."""
    return 1.0/(1.0+10.0**(-dr/400.0))

def sim_goals(elo_a, elo_b, mu=MU_TOTAL):
    """Buts (Poisson) pour des tableaux d'Elo (vectorise sur les simulations)."""
    sup = (elo_a - elo_b)/DIV_GOALS
    la = np.clip((mu+sup)/2.0, 0.12, 6.0)
    lb = np.clip((mu-sup)/2.0, 0.12, 6.0)
    return rng.poisson(la), rng.poisson(lb)

def sim_ko(id_a, id_b):
    """Match a elimination directe vectorise -> renvoie le tableau d'ids gagnants."""
    ea, eb = elo[id_a], elo[id_b]
    ga, gb = sim_goals(ea, eb)
    # prolongation si nul
    tie = ga == gb
    if tie.any():
        sup = (ea-eb)/DIV_GOALS
        la = np.clip(0.275+sup/6.0, 0.05, 3.0)
        lb = np.clip(0.275-sup/6.0, 0.05, 3.0)
        ga = ga + np.where(tie, rng.poisson(la), 0)
        gb = gb + np.where(tie, rng.poisson(lb), 0)
    # tirs au but si toujours nul (avantage tres leger au meilleur)
    still = ga == gb
    if still.any():
        We = expect(ea-eb)
        p_a = np.clip(0.5 + 0.20*(We-0.5), 0.42, 0.58)
        a_pen = rng.random(len(id_a)) < p_a
        ga = ga + np.where(still & a_pen, 1, 0)
        gb = gb + np.where(still & ~a_pen, 1, 0)
    a_win = ga > gb
    return np.where(a_win, id_a, id_b)

# ----------------------------------------------------------------------------
# PHASE DE GROUPES (vectorisee)
# pairings round-robin (indices locaux 0..3) : 6 matchs
# ----------------------------------------------------------------------------
PAIRS = [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2)]

def big_key(pts, gd, gf):
    """Clef de classement : pts > diff > marques > alea (depart. exact)."""
    return (pts*1e9 + (gd+100.0)*1e5 + gf*1e2
            + rng.random(pts.shape))   # alea < 1 ne casse que les egalites exactes

# resultats de groupe : pour chaque groupe, ids tries par rang [N,4]
winners = np.zeros((N_SIMS,12), dtype=np.int32)
runners = np.zeros((N_SIMS,12), dtype=np.int32)
thirds  = np.zeros((N_SIMS,12), dtype=np.int32)
third_key = np.zeros((N_SIMS,12), dtype=np.float64)

for gi, L in enumerate(GROUP_LETTERS):
    ids = np.array(gidx_of[L])                 # 4 ids
    pts = np.zeros((N_SIMS,4)); gf = np.zeros((N_SIMS,4)); ga_ = np.zeros((N_SIMS,4))
    for (x,y) in PAIRS:
        gx, gy = sim_goals(np.full(N_SIMS, elo[ids[x]]), np.full(N_SIMS, elo[ids[y]]))
        gf[:,x]+=gx; ga_[:,x]+=gy; gf[:,y]+=gy; ga_[:,y]+=gx
        pts[:,x]+= np.where(gx>gy,3,np.where(gx==gy,1,0))
        pts[:,y]+= np.where(gy>gx,3,np.where(gx==gy,1,0))
    gd = gf-ga_
    key = big_key(pts, gd, gf)                 # [N,4]
    order = np.argsort(-key, axis=1)           # rang 0=1er ... 3=4e
    rank1, rank2, rank3 = order[:,0], order[:,1], order[:,2]
    winners[:,gi] = ids[rank1]
    runners[:,gi] = ids[rank2]
    thirds[:,gi]  = ids[rank3]
    # clef du 3e (pour departager les meilleurs 3e) avec son propre alea
    r = np.arange(N_SIMS)
    third_key[:,gi] = (pts[r,rank3]*1e9 + (gd[r,rank3]+100.0)*1e5
                       + gf[r,rank3]*1e2 + rng.random(N_SIMS))

# 8 meilleurs 3e -> on retient de quels groupes ils viennent
order_thirds = np.argsort(-third_key, axis=1)   # [N,12] groupes tries
top8_groups  = np.sort(order_thirds[:,:8], axis=1)  # indices de groupe (0..11) qualifies

# ----------------------------------------------------------------------------
# AFFECTATION des 8 meilleurs 3e aux 8 creneaux (eligibilite officielle Annexe C)
# slot -> ensemble de groupes eligibles (indices 0..11 = A..L)
# ----------------------------------------------------------------------------
SLOT_ELIG = {
 'M74': {0,1,2,3,5},   'M77': {2,3,5,6,7},   'M79': {2,4,5,7,8},   'M80': {4,7,8,9,10},
 'M81': {1,4,5,8,9},   'M82': {0,4,7,8,9},   'M85': {4,5,6,8,9},   'M87': {3,4,8,9,11},
}
SLOT_ORDER = ['M74','M77','M79','M80','M81','M82','M85','M87']
ELIG = [SLOT_ELIG[s] for s in SLOT_ORDER]

def match_slots(qual_groups):
    """Couplage parfait creneaux<->groupes (Kuhn). qual_groups = liste de 8 indices."""
    assignment = [-1]*8                     # slot -> group
    def try_assign(slot, seen, gpos):
        for k,g in enumerate(qual_groups):
            if g in ELIG[slot] and not seen[k]:
                seen[k]=True
                if gpos[k]==-1 or try_assign(gpos[k], seen, gpos):
                    gpos[k]=slot; assignment[slot]=g; return True
        return False
    gpos=[-1]*8
    ok=True
    for s in range(8):
        if not try_assign(s,[False]*8,gpos): ok=False
    return assignment, ok

# boucle (legere) sur les sims pour le couplage des 3e
slot_third_team = np.zeros((N_SIMS,8), dtype=np.int32)
group_third_team = {}   # cache: (group idx) -> team id du 3e par sim (vectorise)
for gi in range(12):
    group_third_team[gi] = thirds[:,gi]

fallback = 0
for s in range(N_SIMS):
    qual = list(top8_groups[s])
    assign, ok = match_slots(qual)
    if not ok:
        # secours tres rare : on force une affectation eligible gloutonne
        fallback += 1
        used=set(); assign=[-1]*8
        for slot in range(8):
            for g in qual:
                if g in ELIG[slot] and g not in used:
                    assign[slot]=g; used.add(g); break
    for slot in range(8):
        g = assign[slot]
        slot_third_team[s,slot] = thirds[s,g]

# ----------------------------------------------------------------------------
# CONSTRUCTION DES 16 MATCHS DU R32 (ids par sim) -> indices 0..15 = M73..M88
# ----------------------------------------------------------------------------
A,B,C,D,E,F,G,H,I,J,K,L = range(12)
def W(g): return winners[:,g]
def R(g): return runners[:,g]
T = slot_third_team   # [:,0..7] = 3e affecte a M74,M77,M79,M80,M81,M82,M85,M87

r32_a = np.zeros((N_SIMS,16), dtype=np.int32)
r32_b = np.zeros((N_SIMS,16), dtype=np.int32)
# 0:M73 1:M74 2:M75 3:M76 4:M77 5:M78 6:M79 7:M80 8:M81 9:M82 10:M83 11:M84 12:M85 13:M86 14:M87 15:M88
r32_a[:,0],  r32_b[:,0]  = R(A), R(B)          # M73 RU_A vs RU_B
r32_a[:,1],  r32_b[:,1]  = W(E), T[:,0]        # M74 W_E vs 3e(slot M74)
r32_a[:,2],  r32_b[:,2]  = W(F), R(C)          # M75 W_F vs RU_C
r32_a[:,3],  r32_b[:,3]  = W(C), R(F)          # M76 W_C vs RU_F
r32_a[:,4],  r32_b[:,4]  = W(I), T[:,1]        # M77 W_I vs 3e
r32_a[:,5],  r32_b[:,5]  = R(E), R(I)          # M78 RU_E vs RU_I
r32_a[:,6],  r32_b[:,6]  = W(A), T[:,2]        # M79 W_A vs 3e
r32_a[:,7],  r32_b[:,7]  = W(L), T[:,3]        # M80 W_L vs 3e
r32_a[:,8],  r32_b[:,8]  = W(D), T[:,4]        # M81 W_D vs 3e
r32_a[:,9],  r32_b[:,9]  = W(G), T[:,5]        # M82 W_G vs 3e
r32_a[:,10], r32_b[:,10] = R(K), R(L)          # M83 RU_K vs RU_L
r32_a[:,11], r32_b[:,11] = W(H), R(J)          # M84 W_H vs RU_J
r32_a[:,12], r32_b[:,12] = W(B), T[:,6]        # M85 W_B vs 3e
r32_a[:,13], r32_b[:,13] = W(J), R(H)          # M86 W_J vs RU_H
r32_a[:,14], r32_b[:,14] = W(K), T[:,7]        # M87 W_K vs 3e
r32_a[:,15], r32_b[:,15] = R(D), R(G)          # M88 RU_D vs RU_G

# ----------------------------------------------------------------------------
# DEROULE DES TOURS (arbre officiel)
# ----------------------------------------------------------------------------
w_r32 = np.zeros((N_SIMS,16), dtype=np.int32)
for m in range(16):
    w_r32[:,m] = sim_ko(r32_a[:,m], r32_b[:,m])

# R16 : (M89..M96) couples de matchs R32
R16_PAIRS = [(1,4),(0,2),(3,5),(6,7),(10,11),(8,9),(13,15),(12,14)]
w_r16 = np.zeros((N_SIMS,8), dtype=np.int32)
for i,(x,y) in enumerate(R16_PAIRS):
    w_r16[:,i] = sim_ko(w_r32[:,x], w_r32[:,y])

# QF : (M97..M100)
QF_PAIRS = [(0,1),(4,5),(2,3),(6,7)]
w_qf = np.zeros((N_SIMS,4), dtype=np.int32)
for i,(x,y) in enumerate(QF_PAIRS):
    w_qf[:,i] = sim_ko(w_r16[:,x], w_r16[:,y])

# SF : M101 = QF0 vs QF1 ; M102 = QF2 vs QF3
w_sf = np.zeros((N_SIMS,2), dtype=np.int32)
w_sf[:,0] = sim_ko(w_qf[:,0], w_qf[:,1])
w_sf[:,1] = sim_ko(w_qf[:,2], w_qf[:,3])

# Finale
champion = sim_ko(w_sf[:,0], w_sf[:,1])

# ----------------------------------------------------------------------------
# AGREGATION DES PROBABILITES
# ----------------------------------------------------------------------------
def counts(arr):
    c = np.zeros(NT, dtype=np.int64)
    u,n = np.unique(arr, return_counts=True)
    c[u]=n
    return c

# qualif knockout (R32) : top2 + 8 meilleurs 3e
made_r32 = np.zeros(NT, dtype=np.int64)
for gi in range(12):
    made_r32 += counts(winners[:,gi]); made_r32 += counts(runners[:,gi])
# 3e qualifies
for s in range(0):  # placeholder
    pass
# compter les 3e qualifies via slot_third_team (8 par sim)
for slot in range(8):
    made_r32 += counts(slot_third_team[:,slot])

c_win_grp = np.zeros(NT, dtype=np.int64)
for gi in range(12):
    c_win_grp += counts(winners[:,gi])

c_r16 = np.zeros(NT, dtype=np.int64)
for m in range(16): c_r16 += counts(w_r32[:,m])
c_qf = np.zeros(NT, dtype=np.int64)
for m in range(8): c_qf += counts(w_r16[:,m])
c_sf = np.zeros(NT, dtype=np.int64)
for m in range(4): c_sf += counts(w_qf[:,m])
c_final = counts(w_sf[:,0]) + counts(w_sf[:,1])
c_champ = counts(champion)

P = lambda c: 100.0*c/N_SIMS

# ----------------------------------------------------------------------------
# COTES DE MARCHE (consensus FanDuel/BetMGM, 2-5 juin 2026) -> proba implicite
# ----------------------------------------------------------------------------
MARKET_DEC = {  # cotes decimales approx (american -> decimal)
 'Espagne':5.5,'France':5.8,'Angleterre':7.5,'Bresil':9.5,'Argentine':10.0,
 'Portugal':10.0,'Allemagne':14.0,'Pays-Bas':21.0,'Norvege':34.0,'Belgique':36.0,
 'Colombie':41.0,'Japon':46.0,'Maroc':56.0,'Etats-Unis':56.0,'Uruguay':66.0,'Mexique':67.0,
}
mkt_imp = {k:100.0/v for k,v in MARKET_DEC.items()}

# ----------------------------------------------------------------------------
# SORTIE
# ----------------------------------------------------------------------------
idx_sorted = np.argsort(-c_champ)
print(f"\n=== SIMULATION MONTE CARLO - COUPE DU MONDE 2026 ===")
print(f"{N_SIMS:,} tournois simules | divisor buts={DIV_GOALS:.0f} | mu_total={MU_TOTAL} | bonus hote=+{HOST_BONUS:.0f} Elo")
if fallback: print(f"(affectation 3e de secours sur {fallback} sims)")

print(f"\n{'#':>2} {'Equipe':<18}{'Elo':>6}{'Grp':>4}{'Vainq.%':>9}{'Finale%':>9}{'Demi%':>8}{'1/4%':>8}{'R16%':>8}{'R32%':>8} | {'Marche%':>8}")
print('-'*104)
for rank,i in enumerate(idx_sorted[:24],1):
    name = teams[i]
    base_elo = int(elo[i] - (HOST_BONUS if name in HOSTS else 0))
    mk = mkt_imp.get(name, None)
    mks = f"{mk:7.1f}" if mk is not None else "    -  "
    print(f"{rank:>2} {name:<18}{base_elo:>6}{group_of[i]:>4}"
          f"{P(c_champ)[i]:>9.1f}{P(c_final)[i]:>9.1f}{P(c_sf)[i]:>8.1f}"
          f"{P(c_qf)[i]:>8.1f}{P(c_r16)[i]:>8.1f}{P(made_r32)[i]:>8.1f} | {mks}")

# Verification de coherence (sommes = 100%)
print(f"\nControle  sum(champion)={P(c_champ).sum():.1f}%  sum(finalistes)={P(c_final).sum():.1f}%  "
      f"sum(R32)={P(made_r32).sum():.0f}% (attendu 3200%)")

# Probabilite que la finale soit Espagne-France impossible (meme demie) -> on mesure
# P(France et Espagne toutes deux en demie) et P(elles se rencontrent)
fr, es = team_id['France'], team_id['Espagne']
both_sf = ((w_sf==fr).any(axis=1) | (w_qf==fr).any(axis=1))  # approx
# mesure propre : France et Espagne presentes en 1/2 (w_qf contient les 4 demi-finalistes)
fr_sf = (w_qf==fr).any(axis=1)
es_sf = (w_qf==es).any(axis=1)
print(f"\nFrance en demie : {100*fr_sf.mean():.1f}%   Espagne en demie : {100*es_sf.mean():.1f}%   "
      f"les deux en demie : {100*(fr_sf&es_sf).mean():.1f}%")
# meme demie (M101) ? France via QF0/QF1, Espagne via QF0/QF1 aussi (haut de tableau)
fr_top = (w_qf[:,0]==fr)|(w_qf[:,1]==fr)
es_top = (w_qf[:,0]==es)|(w_qf[:,1]==es)
print(f"France et Espagne dans la meme demi-finale (haut de tableau) : "
      f"{100*(fr_top&es_top).mean():.1f}%")

# Export CSV des probabilites completes
import csv
rows=[]
for i in idx_sorted:
    name=teams[i]
    rows.append([name, group_of[i], int(elo[i]-(HOST_BONUS if name in HOSTS else 0)),
                 round(P(c_champ)[i],2), round(P(c_final)[i],2), round(P(c_sf)[i],2),
                 round(P(c_qf)[i],2), round(P(c_r16)[i],2), round(P(made_r32)[i],2),
                 round(P(c_win_grp)[i],2)])
with open('cdm2026_probabilities.csv','w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['equipe','groupe','elo','vainqueur_%','finaliste_%','demi_%','quart_%','huitieme_%','qualif_R32_%','1er_groupe_%'])
    w.writerows(rows)
print("\nCSV ecrit : cdm2026_probabilities.csv")
