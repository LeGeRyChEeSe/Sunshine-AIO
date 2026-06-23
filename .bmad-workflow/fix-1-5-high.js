export const meta = {
  name: 'bmad-fix-1-5-high',
  description: 'Fix 2 high + 3 medium sur story 1-5',
  phases: [
    { title: 'Re-review high/medium' },
    { title: 'Fix' },
    { title: 'Push final' },
  ],
};

const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/1-5-implementation-des-notifications-systeme-windows';
const worktreePath = repoRoot + '/_bmad-output/worktrees/1-5-implementation-des-notifications-systeme-windows';

const SCHEMA_REVIEW = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } }, required: ['issues', 'verdict'] };
const SCHEMA_FIX = { type: 'object', properties: { fixedCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } }, required: ['fixedCount', 'commitSha', 'status'] };

phase('Re-review');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer sur ' + worktreePath + '/sunshine-aio. Trouve HIGH et MEDIUM restants dans notifications.js, main.js, preload.js, renderer.js, app.test.js. Schema: { issues, verdict }', { phase: 'Re-review', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer sur ' + worktreePath + '/sunshine-aio. Trouve HIGH et MEDIUM security restants. Schema: { issues, verdict }', { phase: 'Re-review', schema: SCHEMA_REVIEW }),
]);

const all = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; }).filter(function(i) { return i.severity === 'high' || i.severity === 'medium'; });
log('Issues restants (high+medium): ' + all.length);

if (all.length === 0) {
  log('Aucun issue restant, skip fix');
} else {
  phase('Fix');
  const fix = await agent('Fix ces HIGH et MEDIUM issues dans ' + worktreePath + '/sunshine-aio:\n' + JSON.stringify(all, null, 2) + '\n\nPour chaque: lis, fix, test. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test.\nCommit: cd ' + worktreePath + ' && git add -A && git commit -m "fix(1-5): final cleanup high+medium issues"\nRetourne: { fixedCount, commitSha, status }', { phase: 'Fix', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') return { ok: false };
}

phase('Push final');
const ship = await agent('Push final pour story 1-5.\n1. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + worktreePath + ' && git push origin ' + branchName + '\n3. gh pr comment 44 --body "Final cleanup: ' + all.length + ' issues (high+medium) addressed. Ready for final review."\n4. Update sprint-status.yaml: 1-5 reste "review".\n5. Retourne: { finalCommit, status }', { phase: 'Push final', schema: { type: 'object', properties: { finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } }, required: ['finalCommit', 'status'] } });

return { ok: true, finalCommit: ship.finalCommit, fixed: all.length };