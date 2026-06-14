// Récupère les Elo à jour depuis eloratings.net et écrit elo.json (à la racine).
// Lancé quotidiennement par GitHub Actions (.github/workflows/update-elo.yml).
// eloratings.net = SPA au-dessus de fichiers TSV : World.tsv (code, rating) + en.teams.tsv (code -> nom).
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dir, '..', 'elo.json');

// nos 48 équipes -> code eloratings (vérifié contre en.teams.tsv)
const CODE = {
  'Mexique':'MX','Corée du Sud':'KR','Afrique du Sud':'ZA','Tchéquie':'CZ',
  'Canada':'CA','Suisse':'CH','Qatar':'QA','Bosnie':'BA',
  'Brésil':'BR','Maroc':'MA','Écosse':'SQ','Haïti':'HT',
  'Etats-Unis':'US','Paraguay':'PY','Australie':'AU','Turquie':'TR',
  'Allemagne':'DE','Equateur':'EC',"Côte d'Ivoire":'CI','Curaçao':'CW',
  'Pays-Bas':'NL','Japon':'JP','Suède':'SE','Tunisie':'TN',
  'Belgique':'BE','Iran':'IR','Egypte':'EG','Nouvelle-Zélande':'NZ',
  'Espagne':'ES','Uruguay':'UY','Arabie saoudite':'SA','Cap-Vert':'CV',
  'France':'FR','Sénégal':'SN','Norvège':'NO','Irak':'IQ',
  'Argentine':'AR','Autriche':'AT','Algérie':'DZ','Jordanie':'JO',
  'Portugal':'PT','Colombie':'CO','Ouzbékistan':'UZ','RD Congo':'CD',
  'Angleterre':'EN','Croatie':'HR','Panama':'PA','Ghana':'GH',
};

async function getTSV(url){
  const r = await fetch(url, { headers:{'User-Agent':'cdm2026-elo-bot'} });
  if(!r.ok) throw new Error('HTTP '+r.status+' on '+url);
  return await r.text();
}

(async () => {
  const [world, names] = await Promise.all([
    getTSV('https://www.eloratings.net/World.tsv'),
    getTSV('https://www.eloratings.net/en.teams.tsv'),
  ]);
  // code -> rating (col 2 = code, col 3 = rating)
  const rating = {};
  world.split('\n').forEach(line=>{ const c=line.split('\t'); if(c.length>3){ rating[c[2]] = parseInt(c[3],10); } });
  // code -> nom anglais (pour vérification)
  const enName = {};
  names.split('\n').forEach(line=>{ const c=line.split('\t'); if(c.length>=2){ enName[c[0]]=c[1]; } });

  const elo = {}; const problems = [];
  for(const [team, code] of Object.entries(CODE)){
    const r = rating[code];
    if(!Number.isFinite(r)){ problems.push(team+' ('+code+') : code introuvable'); continue; }
    // garde-fou : toutes nos 48 équipes (qualifiées CdM) sont > 1500 d'Elo.
    // un rating < 1300 trahit un mauvais code (ex. SC=Seychelles au lieu de SQ=Scotland).
    if(r < 1300){ problems.push(team+' ('+code+') : Elo implausible '+r+' -> '+(enName[code]||'?')); continue; }
    elo[team] = r;
  }
  if(problems.length){ console.error('⚠️ PROBLÈMES de mapping :\n  '+problems.join('\n  ')); }
  if(Object.keys(elo).length < 48){ console.error('Seulement '+Object.keys(elo).length+'/48 équipes — échec.'); process.exit(1); }

  const out = { _source:'eloratings.net', _updated: new Date().toISOString().slice(0,10), elo };
  writeFileSync(OUT, JSON.stringify(out, null, 2));
  console.log('elo.json écrit :', Object.keys(elo).length, 'équipes, MAJ', out._updated);
  // aperçu vérification noms
  ['Espagne','France','Angleterre','Écosse','Etats-Unis'].forEach(t=>{
    console.log('  ', t, '=', elo[t], '(' + (enName[CODE[t]]||'?') + ')');
  });
})().catch(e=>{ console.error('ÉCHEC update-elo:', e.message); process.exit(1); });
