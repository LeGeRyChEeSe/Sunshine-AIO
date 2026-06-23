// BMAD Story Template - reusable via Workflow tool
// Usage: Workflow({script: buildScript(storyKey, storyTitle, storyDescription, storyAc, devInstructions, filesToModify), name: 'story-X-Y'})

// This is a TEMPLATE - copy/paste this into individual story-N-M-v2.js files
// and customize the constants below.

export const meta = {
  name: 'bmad-story-template',
  description: 'Generic BMAD story workflow template',
  phases: [
    { title: 'Setup' },
    { title: 'Dev' },
    { title: 'Review' },
    { title: 'Fix high' },
    { title: 'Fix medium' },
    { title: 'Ship' },
  ],
};

// ============================================================
// CUSTOMIZE THESE FOR EACH STORY:
// ============================================================
const storyKey = 'X-Y-slug';  // e.g., '3-1-implementation-du-scroll-horizontal'
const storyTitle = 'Story Title';
const storyAcBullets = [
  'AC 1 description',
  'AC 2 description',
  'AC 3 description',
];
const devSteps = `
1. Step 1
2. Step 2
3. Verify with npm run lint && npm test
4. Commit
`;
const filesToModify = [
  'sunshine-aio/src/file1.js (new)',
  'sunshine-aio/src/file2.js (modify)',
];
// ============================================================

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
const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story ' + storyKey.split('-')[0] + '.' + storyKey.split('-')[1] + ' (' + storyTitle + ')\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-' + storyKey + '): setup worktree and story file"\n4. Retourne: { worktreePath, branchName, status }', { phase: 'Setup', schema: SCHEMA_SETUP });
if (setup.status !== 'ready') return { ok: false, stage: 'setup' };
log('Worktree pret: ' + setup.worktreePath);

phase('Dev');
const dev = await agent('Agent BMAD Dev. Working dir: ' + setup.worktreePath + '/sunshine-aio. Branch: ' + setup.branchName + '.\n\nSTORY ' + storyKey + ': ' + storyTitle + '.\n\nAC:\n' + storyAcBullets.map(function(b, i) { return '- ' + b; }).join('\n') + '\n\nETAPES:\n' + devSteps + '\n\nFiles to modify:\n' + filesToModify.map(function(f) { return '- ' + f; }).join('\n') + '\n\nVerifier: cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n\nCommit: cd ' + setup.worktreePath + ' && git add -A && git commit -m "feat(' + storyKey + '): ' + storyTitle + '"\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Dev', schema: SCHEMA_DEV });
if (dev.status !== 'ok') return { ok: false, stage: 'dev', blocker: dev.blocker };
log('Dev OK: ' + dev.filesChanged.length + ' files');

phase('Review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer pour story ' + storyKey + ' (' + storyTitle + ') dans ' + setup.worktreePath + '/sunshine-aio. Verifie les AC: ' + storyAcBullets.join(', ') + '. Sois strict sur les edge cases. Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer pour story ' + storyKey + ' dans ' + setup.worktreePath + '/sunshine-aio. Verifie: contextIsolation, channel whitelist, input validation, file path safety, pas d eval/dynamic require. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer pour story ' + storyKey + ' dans ' + setup.worktreePath + '/sunshine-aio. Verifie: code structure, JSDoc, tests utiles (pas mock-only), conventions. Schema: { issues, verdict }', { phase: 'Review', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

let highRounds = 0;
while (currentHigh.length > 0 && highRounds < 3) {
  highRounds++;
  phase('Fix high round ' + highRounds);
  const fix = await agent('Fix HIGH issues dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(' + storyKey + '): round ' + highRounds + ' - high". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
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
  const fix = await agent('Fix MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(' + storyKey + '): round ' + mediumRounds + ' - medium". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Fix medium', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') break;
  const reReview = await agent('Re-review MEDIUM dans ' + setup.worktreePath + '/sunshine-aio. Schema: { issues, verdict }', { phase: 'Fix medium', schema: SCHEMA_REVIEW });
  const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
  if (newMed.length >= currentMedium.length) break;
  currentMedium = newMed;
}

phase('Ship');
const ship = await agent('Ship story ' + storyKey + '.\n1. cd ' + setup.worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + setup.worktreePath + ' && git push origin ' + setup.branchName + '\n3. gh pr create --base bmad --head ' + setup.branchName + ' --title "feat(' + storyKey + '): ' + storyTitle + '" --body "Story ' + storyKey + '. Tests: ' + dev.testsAdded.length + '. ' + currentHigh.length + ' high, ' + currentMedium.length + ' medium."\n4. Update sprint-status.yaml: ' + storyKey + ' in-progress -> review.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, story: storyKey, pr: ship.prUrl, finalCommit: ship.finalCommit, highRemaining: currentHigh.length, mediumRemaining: currentMedium.length, testsAdded: dev.testsAdded.length };