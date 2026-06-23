export const meta = {
  name: 'bmad-story-v2-2-3',
  description: 'Story 2.3 Planet component',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '2-3-creation-du-composant-planet-planetes';
const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/' + storyKey;
const worktreePath = repoRoot + '/_bmad-output/worktrees/' + storyKey;
const storyFileRel = '_bmad-output/implementation-artifacts/stories/' + storyKey + '.md';

const SCHEMA_SETUP = { type: 'object', properties: { worktreePath: { type: 'string' }, branchName: { type: 'string' }, status: { type: 'string', enum: ['ready', 'error'] }, error: { type: 'string' } }, required: ['worktreePath', 'branchName', 'status'] };
const SCHEMA_DEV = { type: 'object', properties: { filesChanged: { type: 'array', items: { type: 'string' } }, testsAdded: { type: 'array', items: { type: 'string' } }, lintPassed: { type: 'boolean' }, testsPassed: { type: 'boolean' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] }, blocker: { type: 'string' } }, required: ['filesChanged', 'lintPassed', 'testsPassed', 'commitSha', 'status'] };
const SCHEMA_REVIEW = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } }, required: ['issues', 'verdict'] };
const SCHEMA_FIX = { type: 'object', properties: { fixedCount: { type: 'number' }, remainingCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } }, required: ['fixedCount', 'remainingCount', 'commitSha', 'status'] };
const SCHEMA_SHIP = { type: 'object', properties: { prUrl: { type: 'string' }, finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } }, required: ['finalCommit', 'status'] };

phase('Setup');
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 2.3 (Planet component)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-2-3): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 2.3: Creation du composant Planet (Planetes).\n\nAC:\n- Planets en positions orbitales autour du sun\n- Apparence procedurale unique par planet\n- Couleur reflete installed status (grayed vs colored)\n\nETAPES:\n1. Creer sunshine-aio/src/three/planet.js:\n   - Classe Planet (extends Object3D)\n   - Geometrie: SphereGeometry avec radius/size configurable\n   - Procedural texture: genere texture noise-based ou couleur unie + rings si gas giant\n   - Position orbitale: calcul depuis index (rayon orbital, angle initial, vitesse)\n   - Couleur: material color modifie selon installed status (gray vs category color)\n   - Animation: rotation sur axe + revolution autour du sun\n   - Methodes: update(deltaTime), setInstalled(bool), getCategory()\n\n2. Creer sunshine-aio/src/three/orbits.js:\n   - Classe Orbit (visualise les orbites en pointilles)\n   - RingGeometry ou LineDashedMaterial\n   - Renderise orbite pour une planete donnee\n\n3. Creer sunshine-aio/src/three/planetFactory.js:\n   - Fonction createPlanetsForCategories(categories)\n   - Genere N planets (1 par category)\n   - Distribue aleatoirement sur orbites\n\n4. Modifier sunshine-aio/src/three/setup.js:\n   - Utiliser planetFactory pour creer les planets\n   - Ajouter a la scene\n\n5. Modifier sunshine-aio/src/state/store.js:\n   - Slice categories: [{id, name, color, apps: []}]\n   - Selector getPlanets()\n\n6. Creer sunshine-aio/src/three/planet.test.js:\n   - Test creation\n   - Test setInstalled change couleur\n   - Test revolution animation (mock time)\n   - Test cleanup dispose\n\n7. Creer sunshine-aio/src/three/planetFactory.test.js:\n   - Test generation N planets\n   - Test distribution unique\n\n8. Verifier: npm run lint && npm test\n\n9. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(2-3): Planet component with orbital positions and procedural appearance"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS + PERFORMANCE reviewer story 2.3 (Planet) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: procedural texture generee, orbits visibles, animation smooth, installed color change fonctionne, FPS stable, pas memory leak. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY + MAINTAINABILITY reviewer story 2.3 dans ' + setup.worktreePath + '/sunshine-aio. Verifie: code modulaire, pas d eval, JSDoc, tests utiles. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(2-3): round ' + highRounds + ' - high". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review HIGH. Schema: { issues, verdict }', { phase: 'Fix high', schema: SCHEMA_REVIEW });
  const newHigh = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'high'; });
  if (newHigh.length >= currentHigh.length) break;
  currentHigh = newHigh;
}

let mediumRounds = 0;
while (currentMedium.length > 0 && mediumRounds < 2) {
  mediumRounds++;
  phase('Fix medium round ' + mediumRounds);
  const fix = await agent('Fix MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(2-3): round ' + mediumRounds + ' - medium". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story 2.3.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(2-3): Planet component with orbital positions" --body "Story 2.3. Tests: ' + dev.testsAdded.length + '. ' + currentHigh.length + ' high, ' + currentMedium.length + ' medium."\n4. Update sprint-status.yaml: 2-3 backlog -> review.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length };