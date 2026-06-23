export const meta = {
  name: 'bmad-story-v2-2-4',
  description: 'Story 2.4 State persistence',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '2-4-implementation-de-la-persistance-d-etat';
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
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 2.4 (persistance d etat)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-2-4): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false };

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 2.4: Implementation de la persistance d etat.\n\nAC:\n- World config persistante entre sessions\n- Installation state saved\n- Au restart, planet colors refletent installed apps\n- Option de regenerer procedural world (FR21) avec installation state preserve\n\nETAPES:\n1. cd ' + setup.worktreePath + '/sunshine-aio\n2. npm install electron-store (alternative: native fs dans app.getPath("userData"))\n\n3. Creer sunshine-aio/src/state/persistence.js:\n   - Wrapper autour de electron-store\n   - Keys: worldConfig, installedApps, navigationHistory\n   - Methods: getWorldConfig(), setWorldConfig(cfg), getInstalledApps(), addInstalledApp(app), removeInstalledApp(appId), regenerateWorld() (genere nouveau seed, preserve apps)\n\n4. Modifier sunshine-aio/src/state/store.js:\n   - Hook avec persistence au boot (hydrate depuis disk)\n   - Save middleware sur les changements d etat importants\n   - Throttle/debounce les saves pour eviter I/O excessif\n\n5. Modifier sunshine-aio/src/three/planetFactory.js:\n   - Utiliser un seed depuis worldConfig.seed pour procedural generation\n   - Permettre regenerate (nouveau seed) tout en gardant apps installed\n\n6. Modifier sunshine-aio/src/renderer.js (ou nouveau handler main process):\n   - Action "Regenerate World" dans settings\n   - Confirme avant regenerer\n\n7. Creer sunshine-aio/src/state/persistence.test.js:\n   - Test save/load\n   - Test regenerate preserves apps\n   - Test corruption recovery (fichier corrompu)\n\n8. Verifier: npm run lint && npm test\n\n9. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(2-4): persistent state with world regen option"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 2.4 (persistence) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: save/load roundtrip, regenerate preserve apps, corruption recovery, throttle/debounce. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer story 2.4 dans ' + setup.worktreePath + '/sunshine-aio. Verifie: file path safe (userData), data sanitized on load, no injection via state. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer story 2.4 dans ' + setup.worktreePath + '/sunshine-aio. Verifie: code modulaire, tests utiles, JSDoc. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(2-4): round ' + highRounds + ' - high". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
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
  const fix = await agent('Fix MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(2-4): round ' + mediumRounds + ' - medium". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story 2.4.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(2-4): State persistence with regen option" --body "Story 2.4. Tests: ' + dev.testsAdded.length + '. ' + currentHigh.length + ' high, ' + currentMedium.length + ' medium."\n4. Update sprint-status.yaml: 2-4 backlog -> review.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length };