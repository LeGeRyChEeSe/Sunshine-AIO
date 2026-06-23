export const meta = {
  name: 'bmad-story-v2-2-1',
  description: 'Story 2.1 Three.js + Zustand',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '2-1-configuration-de-three-js-et-zustand';
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
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad (si existe, remove --force d abord)\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 2.1 (Three.js + Zustand)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-2-1): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };
log('Worktree pret: ' + setup.worktreePath);

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 2.1: Configuration de Three.js et Zustand.\n\nAC:\n- Three.js renders in app window\n- Zustand stores manage app state\n- Canvas 3D displays content\n- FPS monitored and logged\n\nETAPES:\n1. cd ' + setup.worktreePath + '/sunshine-aio\n\n2. Installer les dependances:\n   npm install three zustand\n   npm install --save-dev @types/three (si TS, sinon skip)\n\n3. Creer sunshine-aio/src/three/setup.js:\n   - Configuration renderer (WebGL, antialiasing, shadows)\n   - Configuration scene (background, fog si besoin)\n   - Configuration camera (PerspectiveCamera)\n   - Animation loop avec requestAnimationFrame\n   - Resize handler\n   - FPS monitoring (calcule et log toutes les 1s via logger)\n   - Cleanup (dispose geometries, materials, textures)\n\n4. Creer sunshine-aio/src/state/store.js:\n   - Zustand store avec slices: worldState (planets, sun), installState (apps installed), navigationState (current view)\n   - Persistence middleware (sauvegarde dans localStorage pour l instant, electron-store plus tard)\n   - Actions: setPlanetStatus, addInstalledApp, setCurrentView\n   - Selectors exportes\n\n5. Modifier sunshine-aio/src/renderer.js:\n   - Initialise Three.js scene dans le canvas\n   - Hook avec Zustand pour re-render sur changement state\n   - FPS overlay en haut a droite\n   - Cleanup au unmount\n\n6. Creer sunshine-aio/src/three/setup.test.js:\n   - Test renderer creation\n   - Test camera config\n   - Test resize handler\n   - Test FPS calculation (mock requestAnimationFrame)\n   - Test cleanup dispose\n\n7. Creer sunshine-aio/src/state/store.test.js:\n   - Test initial state\n   - Test setPlanetStatus\n   - Test addInstalledApp\n   - Test persistence (mock localStorage)\n   - Test selectors\n\n8. Verifier: npm run lint && npm test\n\n9. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(2-1): Three.js + Zustand setup with FPS monitoring"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files');

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 2.1 (Three.js + Zustand) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: Three.js rendu vraiment, animation loop pas memory leak, resize debounce, dispose proper, Zustand state immutable, persistence serialisation correcte, FPS calc precis. Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer story 2.1 (Three.js + Zustand) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: contextIsolation preserve (Three.js dans renderer ok mais attention), localStorage data pas sensible, pas de eval dans state updates, WebGL fingerprinting. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer story 2.1 (Three.js + Zustand) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: code structure modulaire (separate three/ et state/), JSDoc, types, tests utiles (pas mock-only), magic numbers documentes. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(2-1): round ' + highRounds + ' - high issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
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
  const fix = await agent('Fix MEDIUM issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(2-1): round ' + mediumRounds + ' - medium issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story 2.1.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(2-1): Configuration Three.js et Zustand" --body "Story 2.1. 3D foundation. Tests: ' + dev.testsAdded.length + ' ajoutes. ' + currentHigh.length + ' high restants, ' + currentMedium.length + ' medium restants."\n4. Update sprint-status.yaml: 2-1 backlog -> review. Commit et push.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length, testsAdded: dev.testsAdded.length };