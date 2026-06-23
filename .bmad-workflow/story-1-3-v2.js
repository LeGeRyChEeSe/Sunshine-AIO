export const meta = {
  name: 'bmad-story-v2-1-3',
  description: 'Story 1.3 IPC Python backend',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '1-3-integration-du-backend-python-existant';
const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/' + storyKey;
const worktreePath = repoRoot + '/_bmad-output/worktrees/' + storyKey;
const storyFileRel = '_bmad-output/implementation-artifacts/stories/' + storyKey + '.md';

const SCHEMA_SETUP = {
  type: 'object',
  properties: {
    worktreePath: { type: 'string' },
    branchName: { type: 'string' },
    status: { type: 'string', enum: ['ready', 'error'] },
    error: { type: 'string' },
  },
  required: ['worktreePath', 'branchName', 'status'],
};

const SCHEMA_DEV = {
  type: 'object',
  properties: {
    filesChanged: { type: 'array', items: { type: 'string' } },
    testsAdded: { type: 'array', items: { type: 'string' } },
    lintPassed: { type: 'boolean' },
    testsPassed: { type: 'boolean' },
    commitSha: { type: 'string' },
    status: { type: 'string', enum: ['ok', 'blocked'] },
    blocker: { type: 'string' },
  },
  required: ['filesChanged', 'lintPassed', 'testsPassed', 'commitSha', 'status'],
};

const SCHEMA_REVIEW = {
  type: 'object',
  properties: {
    issues: { type: 'array', items: {
      type: 'object',
      properties: {
        file: { type: 'string' },
        line: { type: 'number' },
        severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        description: { type: 'string' },
        fix: { type: 'string' },
      },
      required: ['file', 'severity', 'description'],
    }},
    verdict: { type: 'string', enum: ['pass', 'fail'] },
  },
  required: ['issues', 'verdict'],
};

const SCHEMA_FIX = {
  type: 'object',
  properties: {
    fixedCount: { type: 'number' },
    remainingCount: { type: 'number' },
    commitSha: { type: 'string' },
    status: { type: 'string', enum: ['ok', 'blocked'] },
  },
  required: ['fixedCount', 'remainingCount', 'commitSha', 'status'],
};

const SCHEMA_SHIP = {
  type: 'object',
  properties: {
    prUrl: { type: 'string' },
    finalCommit: { type: 'string' },
    status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] },
    blocker: { type: 'string' },
  },
  required: ['finalCommit', 'status'],
};

// PHASE 1: Setup
phase('Setup');
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\n' +
  'ETAPES:\n' +
  '1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad\n' +
  '   Si existe: git worktree remove --force d abord\n\n' +
  '2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 1.3\n\n' +
  '3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-1-3): setup worktree and story file"\n\n' +
  '4. Retourne: { worktreePath, branchName, status }\n',
  { phase: 'Setup', schema: SCHEMA_SETUP });

if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };
log('Worktree pret: ' + setup.worktreePath);

// PHASE 2: Dev
phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\n' +
  'STORY 1.3: Integration backend Python via IPC.\n\n' +
  'AC: ping/pong Electron <-> Python, commandes renderer->main->python.\n\n' +
  'ETAPES:\n' +
  '1. Creer sunshine-aio/src/pythonBridge.js:\n' +
  '   - Classe PythonBridge\n' +
  '   - spawn python (py ou python3) avec child_process\n' +
  '   - Communication JSON-line sur stdin/stdout\n' +
  '   - Queue de requests avec promises\n' +
  '   - Timeout 10s par defaut\n' +
  '   - Cleanup propre (kill SIGTERM puis SIGKILL) au quit\n' +
  '   - Logs via logger (sunshine-aio/src/logger.js)\n' +
  '   - Methodes: send(command, params), ping(), quit()\n\n' +
  '2. Modifier sunshine-aio/src/main.js:\n' +
  '   - Importer PythonBridge\n' +
  '   - Init au app.whenReady\n' +
  '   - ipcMain.handle("python:ping") et ipcMain.handle("python:execute")\n' +
  '   - Cleanup sur app.on("before-quit")\n\n' +
  '3. Modifier sunshine-aio/src/preload.js:\n' +
  '   - Whitelist python:ping et python:execute\n' +
  '   - Expose window.electronAPI.pythonPing et .pythonExecute\n\n' +
  '4. Modifier sunshine-aio/src/renderer.js:\n' +
  '   - Au load, faire un ping\n' +
  '   - Afficher resultat dans le DOM\n\n' +
  '5. Creer sunshine-aio/src/pythonBridge.test.js:\n' +
  '   - Test ping retourne pong\n' +
  '   - Test timeout\n' +
  '   - Test process crash (mock spawn)\n' +
  '   - Test JSON malforme\n' +
  '   - Test cleanup\n' +
  '   - Test requests concurrents\n\n' +
  '6. Creer un script Python minimal pour ping:\n' +
  '   - ../../src/python_ping.py OU commande dans src/main.py\n' +
  '   - Lit JSON {"cmd":"ping"} -> stdout {"result":"pong"}\n\n' +
  '7. Verifier:\n' +
  '   cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n' +
  '   Tous tests passent (logger + errorHandler + pythonBridge + anciens)\n\n' +
  '8. Commit:\n' +
  '   cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(1-3): integrate Python backend via IPC"\n\n' +
  'Retourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }.\n' +
  'Si bloque, status: "blocked" avec blocker.',
  { phase: 'Dev', schema: SCHEMA_DEV });

if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files, ' + dev.testsAdded.length + ' tests (' + dev.commitSha + ')');

// PHASE 3: Review
phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 1.3 Python bridge dans ' + setup.worktreePath + '/sunshine-aio.\n\n' +
    'Verifie:\n' +
    '- ping/pong fonctionne reellement\n' +
    '- Bridge timeout (pas hang infini)\n' +
    '- Bridge crash process (pas zombie)\n' +
    '- JSON parse errors ne crashe pas\n' +
    '- Concurrent requests serialisees (pas corruption stdin/stdout)\n' +
    '- Cleanup au quit (SIGTERM puis SIGKILL)\n' +
    '- python spawn detecte bon interpretateur (py vs python3 vs python)\n\n' +
    'Sois strict. Schema: { issues: [{file, line, severity, description, fix}], verdict }',
    { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer story 1.3 Python bridge dans ' + setup.worktreePath + '/sunshine-aio.\n\n' +
    'Verifie:\n' +
    '- Channel whitelist propre\n' +
    '- python:execute peut-il lancer des commandes arbitraires?\n' +
    '- Path script Python hijackable?\n' +
    '- Buffer overflow stdin/stdout?\n' +
    '- Injection via params JSON sans validation?\n' +
    '- DoS via spam ping?\n' +
    '- Logs contiennent-ils des params (secrets)?\n' +
    '- Zombie process?\n\n' +
    'Sois tres strict. Schema: { issues, verdict }',
    { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer story 1.3 Python bridge dans ' + setup.worktreePath + '/sunshine-aio.\n\n' +
    'Verifie:\n' +
    '- Tests utiles (pas juste mocks qui retournent toujours meme chose)\n' +
    '- Code mort, fonctions non utilisees\n' +
    '- Magic numbers documentes\n' +
    '- Code duplique avec logger.js\n' +
    '- TODOs\n' +
    '- JSDoc sur fonctions publiques\n\n' +
    'Schema: { issues, verdict }',
    { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
const highIssues = allIssues.filter(function(i) { return i.severity === 'high'; });
const mediumIssues = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + highIssues.length + ' high + ' + mediumIssues.length + ' medium + ' + (allIssues.length - highIssues.length - mediumIssues.length) + ' low');

// PHASE 4: Fix HIGH
let highRounds = 0;
let currentHigh = highIssues;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH issues dans ' + setup.worktreePath + '/sunshine-aio.\n\n' +
    'Issues:\n' + JSON.stringify(currentHigh, null, 2) + '\n\n' +
    'Pour chaque: lis, fix, test. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test.\n' +
    'Commit: git add -A && git commit -m "fix(1-3): round ' + highRounds + ' - high issues"\n\n' +
    'Retourne: { fixedCount, remainingCount, commitSha, status }',
    { phase: 'Fix high', schema: SCHEMA_FIX });

  if (fix.status !== 'ok') break;

  const reReview = await agent('Re-review HIGH issues seulement dans ' + setup.worktreePath + '/sunshine-aio. Concis. Schema: { issues, verdict }',
    { phase: 'Fix high', schema: SCHEMA_REVIEW });

  const newHigh = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'high'; });
  if (newHigh.length >= currentHigh.length) break;
  currentHigh = newHigh;
  log('High round ' + highRounds + ': ' + fix.fixedCount + ' fixed, ' + currentHigh.length + ' remaining');
}

// PHASE 5: Fix MEDIUM
let mediumRounds = 0;
let currentMedium = mediumIssues;
while (currentMedium.length > 0 && mediumRounds < 2) {
  mediumRounds++;
  phase('Fix medium round ' + mediumRounds);
  const fix = await agent('Fix MEDIUM issues dans ' + setup.worktreePath + '/sunshine-aio.\n\n' +
    'Issues:\n' + JSON.stringify(currentMedium, null, 2) + '\n\n' +
    'Pour chaque: lis, fix, test.\n' +
    'Commit: git add -A && git commit -m "fix(1-3): round ' + mediumRounds + ' - medium issues"\n\n' +
    'Retourne: { fixedCount, remainingCount, commitSha, status }',
    { phase: 'Fix medium', schema: SCHEMA_FIX });

  if (fix.status !== 'ok') break;

  const reReview = await agent('Re-review MEDIUM issues dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }',
    { phase: 'Fix medium', schema: SCHEMA_REVIEW });

  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
  log('Medium round ' + mediumRounds + ': ' + fix.fixedCount + ' fixed, ' + currentMedium.length + ' remaining');
}

// PHASE 6: Ship
phase('Ship');
const ship = await agent('Ship story 1.3.\n\n' +
  '1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n' +
  '   Si pas OK, fix immediatement\n' +
  '2. cd ' + setup.worktreePath + '\n' +
  '3. git push origin ' + setup.branchName + '\n' +
  '4. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(1-3): Integration du backend Python existant" --body "Story 1.3 IPC Python backend. AC validates. Tests: ' + dev.testsAdded.length + ' ajoutes. 0 high restants, ' + currentMedium.length + ' medium restants."\n' +
  '5. Update _bmad-output/implementation-artifacts/sprint-status.yaml: 1-3 in-progress -> review. Commit: git add -A && git commit -m "chore(1-3): mark review"\n' +
  '6. git push origin ' + setup.branchName + '\n\n' +
  'Retourne: { prUrl, finalCommit, status }\n' +
  'Si gh pas dispo: status "pushed-no-pr"',
  { phase: 'Ship', schema: SCHEMA_SHIP });

return {
  ok: true,
  story: storyKey,
  pr: ship.prUrl,
  finalCommit: ship.finalCommit,
  highRemaining: currentHigh.length,
  mediumRemaining: currentMedium.length,
  testsAdded: dev.testsAdded.length,
  highRounds: highRounds,
  mediumRounds: mediumRounds,
};