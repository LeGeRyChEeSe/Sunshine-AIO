export const meta = {
  name: 'bmad-story-v2-1-4',
  description: 'Story 1.4 Admin privileges + system tray',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '1-4-configuration-des-privileges-admin-et-du-system-tray';
const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/' + storyKey;
const worktreePath = repoRoot + '/_bmad-output/worktrees/' + storyKey;
const storyFileRel = '_bmad-output/implementation-artifacts/stories/' + storyKey + '.md';

const SCHEMA_SETUP = {
  type: 'object',
  properties: { worktreePath: { type: 'string' }, branchName: { type: 'string' }, status: { type: 'string', enum: ['ready', 'error'] }, error: { type: 'string' } },
  required: ['worktreePath', 'branchName', 'status'],
};

const SCHEMA_DEV = {
  type: 'object',
  properties: { filesChanged: { type: 'array', items: { type: 'string' } }, testsAdded: { type: 'array', items: { type: 'string' } }, lintPassed: { type: 'boolean' }, testsPassed: { type: 'boolean' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] }, blocker: { type: 'string' } },
  required: ['filesChanged', 'lintPassed', 'testsPassed', 'commitSha', 'status'],
};

const SCHEMA_REVIEW = {
  type: 'object',
  properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } },
  required: ['issues', 'verdict'],
};

const SCHEMA_FIX = {
  type: 'object',
  properties: { fixedCount: { type: 'number' }, remainingCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } },
  required: ['fixedCount', 'remainingCount', 'commitSha', 'status'],
};

const SCHEMA_SHIP = {
  type: 'object',
  properties: { prUrl: { type: 'string' }, finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } },
  required: ['finalCommit', 'status'],
};

phase('Setup');
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad (si existe, remove --force d abord)\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 1.4 (Admin privileges + system tray)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-1-4): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };
log('Worktree pret: ' + setup.worktreePath);

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 1.4: Configuration des privileges admin et du system tray.\n\nAC: \n- App peut demander privileges admin si necessaire\n- App peut etre minimisée dans system tray\n- Click sur tray icon restaure la fenetre\n- Right-click sur tray icon montre menu Open/Quit\n\nETAPES:\n1. Creer sunshine-aio/src/tray.js:\n   - Classe TrayManager\n   - Cree tray icon avec icone\n   - Menu contextuel (Open, Quit)\n   - Click gauche restaure la fenetre\n   - Evenements sur minimize vers tray\n\n2. Modifier sunshine-aio/src/main.js:\n   - Importer TrayManager\n   - Init apres createWindow\n   - Sur window close: si minimize-to-tray enabled, cacher au lieu de quitter\n   - Sur before-quit: cleanup tray\n   - Hook pour demande elevation admin via app.setAppUserModelId + ShellExecute "runas"\n   - Note: le binaire lui-meme est lance en admin grace a electron-builder Squirrel ou electron-forge\n\n3. Modifier sunshine-aio/src/preload.js:\n   - Whitelist tray:minimize-to-tray et tray:set-minimize-behavior\n   - Expose window.electronAPI.setMinimizeToTray(enabled)\n\n4. Modifier sunshine-aio/src/renderer.js:\n   - Settings UI pour activer/desactiver minimize-to-tray\n   - Toggle persiste via electron-store ou JSON\n\n5. Creer sunshine-aio/src/tray.test.js:\n   - Test tray creation\n   - Test menu items\n   - Test click handlers\n   - Test cleanup\n   - Test minimize behavior\n\n6. Note: pour les privileges admin, le pattern est:\n   - electron-forge Squirrel peut etre configure pour requerir admin a l install\n   - Pour elevation runtime: ShellExecute avec "runas" verb\n   - Documenter dans README comment builder l app en admin-required\n\n7. Verifier: cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n8. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(1-4): admin privileges and system tray"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files');

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 1.4 (admin + tray) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: tray icon apparait, menu contextuel fonctionnel, minimize-to-tray cache vraiment la fenetre (pas juste minimise), cleanup au quit pas de tray orphelin, elevation admin via runas fonctionne sur Windows. Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer story 1.4 (admin + tray) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: elevation admin pas abusif (juste quand necessaire), tray icon path pas hijackable, runas args sanitises, minimize-to-tray peut-etre desactive par utilisateur, persistence des settings securisee. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer story 1.4 (admin + tray) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: tests utiles, code mort, magic numbers, conventions, JSDoc, TODOs. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Pour chaque: lis, fix, test. Commit: "fix(1-4): round ' + highRounds + ' - high issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review HIGH dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix high', schema: SCHEMA_REVIEW });
  const newHigh = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'high'; });
  if (newHigh.length >= currentHigh.length) break;
  currentHigh = newHigh;
  log('High round ' + highRounds + ': ' + fix.fixedCount + ' fixed, ' + currentHigh.length + ' remaining');
}

let mediumRounds = 0;
while (currentMedium.length > 0 && mediumRounds < 2) {
  mediumRounds++;
  phase('Fix medium round ' + mediumRounds);
  const fix = await agent('Fix MEDIUM issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(1-4): round ' + mediumRounds + ' - medium issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
  log('Medium round ' + mediumRounds + ': ' + fix.fixedCount + ' fixed, ' + currentMedium.length + ' remaining');
}

phase('Ship');
const ship = await agent('Ship story 1.4.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(1-4): Configuration privileges admin et system tray" --body "Story 1.4. Tests: ' + dev.testsAdded.length + ' ajoutes. ' + currentHigh.length + ' high restants, ' + currentMedium.length + ' medium restants."\n4. Update sprint-status.yaml: 1-4 in-progress -> review. Commit et push.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length, testsAdded: dev.testsAdded.length };