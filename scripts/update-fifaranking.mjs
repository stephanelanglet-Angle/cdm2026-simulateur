// Récupère le Classement mondial FIFA officiel (rang + points) et écrit fifa.json (racine).
// Source : API JSON interne FIFA (inside.fifa.com). Lancé par GitHub Actions (quotidien).
// Sert de DERNIER critère de départage (Art. 13, étape 3) dans le classement des groupes.
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dir, '..', 'fifa.json');

// nos 48 équipes -> code FIFA (3 lettres, ≠ ISO strict : GER, NED, POR, CRO, SUI...)
const CODE = {
  'Mexique':'MEX','Corée du Sud':'KOR','Afrique du Sud':'RSA','Tchéquie':'CZE',
  'Canada':'CAN','Suisse':'SUI','Qatar':'QAT','Bosnie':'BIH',
  'Brésil':'BRA','Maroc':'MAR','Écosse':'SCO','Haïti':'HAI',
  'Etats-Unis':'USA','Paraguay':'PAR','Australie':'AUS','Turquie':'TUR',
  'Allemagne':'GER','Equateur':'ECU',"Côte d'Ivoire":'CIV','Curaçao':'CUW',
  'Pays-Bas':'NED','Japon':'JPN','Suède':'SWE','Tunisie':'TUN',
  'Belgique':'BEL','Iran':'IRN','Egypte':'EGY','Nouvelle-Zélande':'NZL',
  'Espagne':'ESP','Uruguay':'URU','Arabie saoudite':'KSA','Cap-Vert':'CPV',
  'France':'FRA','Sénégal':'SEN','Norvège':'NOR','Irak':'IRQ',
  'Argentine':'ARG','Autriche':'AUT','Algérie':'ALG','Jordanie':'JOR',
  'Portugal':'POR','Colombie':'COL','Ouzbékistan':'UZB','RD Congo':'COD',
  'Angleterre':'ENG','Croatie':'CRO','Panama':'PAN','Ghana':'GHA',
};

(async () => {
  // 1) trouver le dateId du classement le plus récent (la page embarque les dates)
  const html = await (await fetch('https://inside.fifa.com/fifa-world-ranking/men', { headers:{'User-Agent':'Mozilla/5.0 cdm2026-bot'} })).text();
  const dates = [...html.matchAll(/\{"id":"(id\d+)","iso":"([^"]+)"/g)].map(m => ({ id:m[1], iso:m[2] }));
  if (!dates.length) throw new Error('aucun dateId trouvé sur la page FIFA');
  const latest = dates.sort((a,b) => a.iso < b.iso ? 1 : -1)[0];

  // 2) récupérer les rankings
  const url = `https://inside.fifa.com/api/ranking-overview?locale=en&dateId=${latest.id}`;
  const data = await (await fetch(url, { headers:{'User-Agent':'Mozilla/5.0 cdm2026-bot','Accept':'application/json'} })).json();
  const byCode = {};
  (data.rankings || []).forEach(r => { const it = r.rankingItem; if (it && it.countryCode) byCode[it.countryCode] = { rank:it.rank, points:it.totalPoints }; });

  const fifa = {}; const problems = [];
  for (const [team, code] of Object.entries(CODE)) {
    const e = byCode[code];
    if (!e || !Number.isFinite(e.points)) { problems.push(team+' ('+code+') : introuvable'); continue; }
    if (e.points < 1100) { problems.push(team+' ('+code+') : points implausibles '+e.points+' (mauvais code ?)'); continue; }
    fifa[team] = { rank:e.rank, points:e.points };
  }
  if (problems.length) console.error('⚠️ PROBLÈMES :\n  ' + problems.join('\n  '));
  if (Object.keys(fifa).length < 44) { console.error('Seulement '+Object.keys(fifa).length+'/48 équipes — échec.'); process.exit(1); }

  const out = { _source:'inside.fifa.com', _updated:new Date().toISOString().slice(0,10), _rankingDate:latest.iso.slice(0,10), fifa };
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  console.log('fifa.json écrit :', Object.keys(fifa).length, 'équipes, classement du', out._rankingDate);
  ['Espagne','France','Mexique','Etats-Unis','Écosse','Curaçao'].forEach(t => console.log('  ', t, '=', fifa[t] ? ('rang '+fifa[t].rank+', '+fifa[t].points+' pts') : '(manquant)'));
})().catch(e => { console.error('ÉCHEC update-fifaranking:', e.message); process.exit(1); });
