export const meta = {
  name: 'bmad-story-v2-1-5',
  description: 'Story 1.5 Notifications systeme Windows',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

const storyKey = '1-5-implementation-des-notifications-systeme-windows';
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
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad (si existe, remove --force d abord)\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story 1.5 (Windows notifications)\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-1-5): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup', error: setup.error };
log('Worktree pret: ' + setup.worktreePath);

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY 1.5: Implementation des notifications systeme Windows.\n\nAC: \n- Notification "Installation Complete" apres install\n- Notification "Updates Available" quand updates dispo\n- Notification error si install fail\n- Click sur notification ouvre l app\n\nETAPES:\n1. Creer sunshine-aio/src/notifications.js:\n   - Classe NotificationManager (wrapper sur Electron Notification)\n   - Methodes: notifyInstallComplete(appName), notifyUpdateAvailable(apps), notifyError(message)\n   - Click handler pour focus app\n   - Icon path configurable\n   - Logs via logger (story 1.2)\n   - Permission check / fallback si pas supporté\n\n2. Modifier sunshine-aio/src/main.js:\n   - Importer NotificationManager\n   - Init au app.whenReady (apres logger)\n   - Hook avec pythonBridge pour notify sur install/updates/error\n   - app.setAppUserModelId pour notifications Windows correctes\n\n3. Modifier sunshine-aio/src/preload.js:\n   - Whitelist notification channels: notification:test, notification:install-complete, notification:update-available, notification:error\n   - Expose window.electronAPI.notifyInstallComplete, notifyUpdateAvailable, notifyError\n\n4. Modifier sunshine-aio/src/renderer.js:\n   - Exemple bouton "Test Notification" qui appelle notifyInstallComplete\n   - Affichage des notifications recues (eventuel echo)\n\n5. Creer sunshine-aio/src/notifications.test.js:\n   - Test creation notification avec titre/body/icon\n   - Test click handler\n   - Test fallback si Notification non supporté\n   - Test click-to-focus (mock window)\n\n6. Verifier: cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n7. Commit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(1-5): implement Windows system notifications"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files');

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer story 1.5 (notifications) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: notification apparait vraiment, click focus app, appUserModelId set, fallback si non supporté, threadsafe (notifications depuis main process). Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer story 1.5 (notifications) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: appUserModelId unique (pas spoof), notification body sanitisé (pas XSS), icon path pas hijackable, channel whitelist preload propre, click handler pas abusif. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer story 1.5 (notifications) dans ' + setup.worktreePath + '/sunshine-aio. Verifie: tests utiles, JSDoc, conventions, code duplique avec logger. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(1-5): round ' + highRounds + ' - high issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
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
  const fix = await agent('Fix MEDIUM issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(1-5): round ' + mediumRounds + ' - medium issues". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story 1.5.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(1-5): Implementation des notifications systeme Windows" --body "Story 1.5. Tests: ' + dev.testsAdded.length + ' ajoutes. ' + currentHigh.length + ' high restants, ' + currentMedium.length + ' medium restants."\n4. Update sprint-status.yaml: 1-5 in-progress -> review. Commit et push.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length, testsAdded: dev.testsAdded.length };