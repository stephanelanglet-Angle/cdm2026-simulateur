// Génère thirds.json : la table OFFICIELLE FIFA 2026 d'affectation des 8 meilleurs 3es
// aux 8 matchs du Round of 32 (495 combinaisons = C(12,8)). Source : Wikipédia
// Template:2026_FIFA_World_Cup_third-place_table (HTML statique, transclus de l'Annexe C FIFA).
// Données STATIQUES (la table ne change jamais) -> à lancer une fois, puis commit thirds.json.
//
// Sortie : { "<combo trié 8 lettres>": "<8 chars = 3e affecté, dans l'ordre des matchs 74,77,79,80,81,82,85,87>" }
// Ex. "ABCDEFGH":"CD..." -> match 74 reçoit le 3e de C, match 77 celui de D, etc.
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dir, '..', 'thirds.json');

// Les 8 matchs du R32 qui reçoivent un 3e, et le vainqueur de groupe qui y joue.
const MATCH_WINNER = { 74:'E', 77:'I', 79:'A', 80:'L', 81:'D', 82:'G', 85:'B', 87:'K' };
const MATCH_ORDER = [74,77,79,80,81,82,85,87];
// Ordre des colonnes d'affectation dans la table (en-tête : 1A,1B,1D,1E,1G,1I,1K,1L).
const COL_WINNERS = ['A','B','D','E','G','I','K','L'];

const clean = s => s.replace(/<[^>]+>/g,'').replace(/&#160;/g,' ').replace(/\s+/g,' ').trim();
const cellsOf = r => [...r.matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/g)].map(m => clean(m[1]));

const html = await (await fetch('https://en.wikipedia.org/wiki/Template:2026_FIFA_World_Cup_third-place_table',
  { headers:{'User-Agent':'Mozilla/5.0 cdm2026-bot'} })).text();
const cap = html.indexOf('Combinations of matches in the round of 32');
if (cap < 0) throw new Error('table introuvable (caption absente)');
const tbl = html.slice(html.lastIndexOf('<table', cap), html.indexOf('</table>', cap));
const rows = tbl.split(/<tr[ >]/).slice(1);

const table = {}; const problems = []; let n = 0;
for (const r of rows) {
  const thirds = cellsOf(r).map(c => (c.match(/^3([A-L])$/) || [])[1]).filter(Boolean); // 8 lettres, ordre colonnes
  if (thirds.length !== 8) continue;                       // saute l'en-tête et toute ligne non conforme
  n++;
  const col = {}; COL_WINNERS.forEach((w,i) => col[w] = thirds[i]);   // vainqueur -> 3e affecté
  const assign = MATCH_ORDER.map(m => col[MATCH_WINNER[m]]).join('');  // dans l'ordre des matchs
  const combo = [...assign].sort().join('');                          // combinaison = ensemble des 3es

  // invariants par ligne
  if (new Set(assign).size !== 8) problems.push('option '+n+' : 3es dupliqués ('+assign+')');
  MATCH_ORDER.forEach((m,i) => { if (assign[i] === MATCH_WINNER[m]) problems.push('option '+n+' : match '+m+' = 3e de son propre groupe ('+MATCH_WINNER[m]+')'); });
  if (table[combo]) problems.push('combo dupliqué : '+combo);
  table[combo] = assign;
}

// invariants globaux
if (n !== 495) problems.push('lignes parsées = '+n+' (attendu 495)');
if (Object.keys(table).length !== 495) problems.push('combos uniques = '+Object.keys(table).length+' (attendu 495)');

// TS_ELIG dérivé : par match, l'ensemble des 3es jamais affectés
const elig = {}; MATCH_ORDER.forEach(m => elig[m] = new Set());
for (const combo in table) { const a = table[combo]; MATCH_ORDER.forEach((m,i) => elig[m].add(a[i])); }
const eligStr = {}; MATCH_ORDER.forEach(m => eligStr[m] = [...elig[m]].sort().join(''));
const EXPECTED_ELIG = { 74:'ABCDF', 77:'CDFGH', 79:'CEFHI', 80:'EHIJK', 81:'BEFIJ', 82:'AEHIJ', 85:'EFGIJ', 87:'DEIJL' };
MATCH_ORDER.forEach(m => { if (eligStr[m] !== EXPECTED_ELIG[m]) problems.push('TS_ELIG match '+m+' dérivé '+eligStr[m]+' ≠ attendu '+EXPECTED_ELIG[m]); });

console.log('Lignes parsées :', n, '| combos uniques :', Object.keys(table).length);
console.log('TS_ELIG dérivé de la table :');
MATCH_ORDER.forEach(m => console.log('  match '+m+' (1'+MATCH_WINNER[m]+') : '+eligStr[m]+(eligStr[m]===EXPECTED_ELIG[m]?' ✓':' ✗ attendu '+EXPECTED_ELIG[m])));
if (problems.length) { console.error('\n⚠️ PROBLÈMES ('+problems.length+') :\n  '+problems.slice(0,20).join('\n  ')); process.exit(1); }

writeFileSync(OUT, JSON.stringify(table));
console.log('\nthirds.json écrit (' + Object.keys(table).length + ' combinaisons).');
console.log('Échantillons :');
[['EFGHIJKL'],['ABCDEFGH'],['CDFGHIJK']].forEach(([c]) => console.log('  '+c+' ->', table[[...c].sort().join('')] || '(absent)'));
