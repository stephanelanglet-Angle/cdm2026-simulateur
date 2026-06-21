// Récupère les points de fair-play (discipline, Art. 13) par équipe depuis Wikipédia et écrit fairplay.json (racine).
// 1 page par groupe (A..L) ; la colonne "Score" est déjà calculée au barème FIFA
// (−1 jaune, −3 2e jaune/expulsion indirecte, −4 rouge direct, −5 jaune + rouge direct).
// Critère f) (étape 2) du départage des groupes. Lancé par GitHub Actions (toutes les 2h).
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dir, '..', 'fairplay.json');
const GROUPS = 'ABCDEFGHIJKL'.split('');

function parseDiscipline(html){
  const idx = html.indexOf('id="Discipline"');
  if (idx < 0) return {};
  const after = html.slice(idx);
  const ts = after.indexOf('<table'), te = after.indexOf('</table>');
  if (ts < 0 || te < 0) return {};
  const tbl = after.slice(ts, te);
  const out = {};
  for (const r of tbl.split(/<tr[ >]/).slice(1)) {
    // le titre varie : "X national football team" OU "X national soccer team" (USA, RSA...)
    // titre : "X [men's] national football|soccer team" (USA/Canada = "men's")
    const tm = (r.match(/title="([^"]+?)(?: men(?:&#39;|')s)? national (?:football|soccer) team"/) || [])[1];
    if (!tm) continue;
    // la colonne Score est un <th> en fin de ligne -> capturer td ET th, prendre la dernière cellule
    const cells = [...r.matchAll(/<t[dh][^>]*>([\s\S]*?)<\/t[dh]>/g)].map(m => m[1]);
    if (!cells.length) continue;
    const last = cells[cells.length - 1].replace(/<[^>]+>/g, '').replace(/[−–—]/g, '-').trim();
    const score = parseInt(last, 10);
    if (Number.isFinite(score)) out[tm] = score;   // équipe absente = 0 carton (géré côté app)
  }
  return out;
}

(async () => {
  const points = {}; let groupsOk = 0;
  for (const g of GROUPS) {
    try {
      const html = await (await fetch('https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_Group_' + g, { headers:{'User-Agent':'Mozilla/5.0 cdm2026-bot'} })).text();
      const d = parseDiscipline(html);
      if (Object.keys(d).length) { Object.assign(points, d); groupsOk++; }
    } catch (e) { console.error('Groupe ' + g + ' échec:', e.message); }
  }
  const out = { _source:'en.wikipedia.org (Discipline)', _updated:new Date().toISOString().slice(0,10), points };
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  console.log('fairplay.json écrit :', Object.keys(points).length, 'équipes,', groupsOk, '/12 groupes.');
  Object.entries(points).slice(0, 10).forEach(([t, p]) => console.log('  ', t, '=', p));
})().catch(e => { console.error('ÉCHEC update-fairplay:', e.message); process.exit(1); });
