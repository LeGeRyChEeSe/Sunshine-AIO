export const meta = {
  name: 'bmad-fix-1-3-high',
  description: 'Fix 3 high issues sur story 1-3',
  phases: [
    { title: 'Re-review pour identifier high' },
    { title: 'Fix high' },
    { title: 'Vérification + push' },
  ],
};

const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/1-3-integration-du-backend-python-existant';
const worktreePath = repoRoot + '/_bmad-output/worktrees/1-3-integration-du-backend-python-existant';

const SCHEMA_REVIEW = {
  type: 'object',
  properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } },
  required: ['issues', 'verdict'],
};

const SCHEMA_FIX = {
  type: 'object',
  properties: { fixedCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } },
  required: ['fixedCount', 'commitSha', 'status'],
};

const SCHEMA_SHIP = {
  type: 'object',
  properties: { finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } },
  required: ['finalCommit', 'status'],
};

phase('Re-review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer sur ' + worktreePath + '/sunshine-aio. Trouve les HIGH issues qui restent dans pythonBridge.js, main.js, preload.js, renderer.js, python_ping.py. Sois strict. Schema: { issues, verdict }', { phase: 'Re-review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer sur ' + worktreePath + '/sunshine-aio. Trouve les HIGH security issues. Schema: { issues, verdict }', { phase: 'Re-review', schema: SCHEMA_REVIEW }),
]);

const allHigh = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; }).filter(function(i) { return i.severity === 'high'; });
log('High issues: ' + allHigh.length);

if (allHigh.length === 0) {
  log('Aucun high issue restant, skip fix');
} else {
  phase('Fix high');
  const fix = await agent('Fix ces HIGH issues dans ' + worktreePath + '/sunshine-aio:\n' + JSON.stringify(allHigh, null, 2) + '\n\nPour chaque: lis, fix, test. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test.\nCommit: cd ' + worktreePath + ' && git add -A && git commit -m "fix(1-3): final high issues cleanup"\nRetourne: { fixedCount, commitSha, status }', { phase: 'Fix high', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') return { ok: false, blocker: fix };
}

phase('Ship');
const ship = await agent('Push final pour story 1-3.\n1. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + worktreePath + ' && git push origin ' + branchName + '\n3. gh pr comment 42 --body "Final fix: ' + (allHigh.length || 0) + ' high issues addressed. Ready for final review." (si gh dispo)\n4. Update sprint-status.yaml: 1-3 reste "review" (deja).\n5. Retourne: { finalCommit, status }', { phase: 'Ship', schema: SCHEMA_SHIP });

return { ok: true, finalCommit: ship.finalCommit, highFixed: allHigh.length };