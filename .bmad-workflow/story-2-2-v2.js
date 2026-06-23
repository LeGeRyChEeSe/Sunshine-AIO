export const meta = {
  name: 'bmad-story-v2-2-2',
  description: 'Story 2.2 Sun component',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '2-2-creation-du-composant-sun-soleil';
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
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 2.2 (Sun/Soleil component)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-2-2): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };
log('Worktree pret: ' + setup.worktreePath);

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 2.2: Creation du composant Sun (Soleil).\n\nAC:\n- Sun avec orange/yellow glow effects au centre\n- Animation de pulsation\n- Indicateurs visuels pour core tools installes (Sunshine/Apollo, VDD, Playnite)\n\nETAPES:\n1. cd ' + setup.worktreePath + '/sunshine-aio\n\n2. Creer sunshine-aio/src/three/sun.js:\n   - Classe Sun (extends Object3D de Three.js)\n   - Geometrie: SphereGeometry avec radius configurable\n   - Material: MeshStandardMaterial avec emissive orange/yellow\n   - Glow effect: SpriteLayer ou post-processing ou simple halo via SphereGeometry transparente plus grande\n   - Pulsing animation (scale modifie selon sin(time))\n   - Core tools indicators: 3 petits satellites ou icones autour du sun\n   - methodes: update(deltaTime), setInstalledTools({sunshine, vdd, playnite})\n\n3. Creer sunshine-aio/src/three/sun.test.js:\n   - Test Sun creation\n   - Test pulsation animation (mock time)\n   - Test setInstalledTools met a jour indicateurs\n   - Test cleanup dispose\n\n4. Modifier sunshine-aio/src/three/setup.js (si necessaire):\n   - Ajouter le sun a la scene\n   - Wire avec Zustand store pour core tools status\n\n5. Modifier sunshine-aio/src/state/store.js (si necessaire):\n   - Ajouter slice coreTools: {sunshine: bool, vdd: bool, playnite: bool}\n\n6. Verifier: npm run lint && npm test\n\n7. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(2-2): Sun component with glow and core tools indicators"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files');

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 2.2 (Sun component) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: Sun vraiment rendu, glow fonctionne, pulsation smooth (pas janky), core tools indicators reactifs, performance 60 FPS, cleanup dispose. Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY + MAINTAINABILITY reviewer story 2.2 dans ' + setup.worktreePath + '/sunshine-aio. Verifie: pas de eval/dynamic require, animation values sane, code modulaire. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('PERFORMANCE reviewer story 2.2 dans ' + setup.worktreePath + '/sunshine-aio. Verifie: pas de memory leak (geometry/material non disposes), frame rate stable, shadow maps config, render call optimal. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(2-2): round ' + highRounds + ' - high". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review HIGH dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix high', schema: SCHEMA_REVIEW });
  const newHigh = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'high'; });
  if (newHigh.length >= currentHigh.length) break;
  currentHigh = newHigh;
}

let mediumRounds = 0;
while (currentMedium.length > 0 && mediumRounds < 2) {
  mediumRounds++;
  phase('Fix medium round ' + mediumRounds);
  const fix = await agent('Fix MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(2-2): round ' + mediumRounds + ' - medium". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story 2.2.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(2-2): Sun component avec glow et core tools" --body "Story 2.2. Tests: ' + dev.testsAdded.length + '. ' + currentHigh.length + ' high, ' + currentMedium.length + ' medium."\n4. Update sprint-status.yaml: 2-2 backlog -> review.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length };