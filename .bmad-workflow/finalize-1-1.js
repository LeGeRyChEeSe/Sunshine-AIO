export const meta = {
  name: 'bmad-finalize-1-1',
  description: 'Finalize story 1-1 (Round 9 cleanup + create PR)',
  phases: [
    { title: 'Re-review 1-1' },
    { title: 'Fix medium/low' },
    { title: 'Push + create PR' },
  ],
};

const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';
const branchName = 'story/1-1-initialisation-electron-forge-vite';
const worktreePath = repoRoot + '/_bmad-output/worktrees/story-1-1-initialisation-electron-forge-vite';

const SCHEMA_REVIEW = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } }, required: ['issues', 'verdict'] };
const SCHEMA_FIX = { type: 'object', properties: { fixedCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } }, required: ['fixedCount', 'commitSha', 'status'] };
const SCHEMA_SHIP = { type: 'object', properties: { prUrl: { type: 'string' }, finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } }, required: ['finalCommit', 'status'] };

phase('Re-review 1-1');
const reviews = await parallel([
  () => agent('CORRECTNESS reviewer pour finaliser story 1-1 (Electron Forge + Vite init) dans ' + worktreePath + '/sunshine-aio. Trouve TOUS les issues restants (high/medium/low). Story dit Round 9 review: 3 Medium, 4 Low. Verifie qu ils sont bien fixes. Schema: { issues, verdict }', { phase: 'Re-review 1-1', schema: SCHEMA_REVIEW }),
  () => agent('SECURITY reviewer pour story 1-1 dans ' + worktreePath + '/sunshine-aio. Verifie: contextIsolation, nodeIntegration, sandbox, preload security, asar config, fuses config (RunAsNode false, EnableEmbeddedAsarIntegrityValidation true). Schema: { issues, verdict }', { phase: 'Re-review 1-1', schema: SCHEMA_REVIEW }),
  () => agent('MAINTAINABILITY reviewer pour story 1-1 dans ' + worktreePath + '/sunshine-aio. Verifie: tests utiles, structure (main/preload/renderer separation), package.json propre, forge.config.js bien organise, README a jour. Schema: { issues, verdict }', { phase: 'Re-review 1-1', schema: SCHEMA_REVIEW }),
]);

const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
const mediumLow = allIssues.filter(function(i) { return i.severity === 'medium' || i.severity === 'low'; });
const high = allIssues.filter(function(i) { return i.severity === 'high'; });
log('Issues: ' + high.length + ' high, ' + mediumLow.length + ' medium+low');

if (high.length > 0 || mediumLow.length > 0) {
  phase('Fix');
  const fix = await agent('Fix ces issues dans ' + worktreePath + '/sunshine-aio:\n\nHIGH:\n' + JSON.stringify(high, null, 2) + '\n\nMEDIUM+LOW:\n' + JSON.stringify(mediumLow, null, 2) + '\n\nPour chaque: lis, fix, test. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test.\nCommit: cd ' + worktreePath + ' && git add -A && git commit -m "fix(1-1): Round 9 cleanup - address remaining medium/low issues"\nRetourne: { fixedCount, commitSha, status }', { phase: 'Fix', schema: SCHEMA_FIX });
  if (fix.status !== 'ok') return { ok: false };
}

phase('Push + PR');
const ship = await agent('Push et creer PR pour story 1-1.\n1. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + worktreePath + ' && git push origin ' + branchName + ' (ou git push -u origin ' + branchName + ' si premiere fois)\n3. gh pr create --base bmad --head ' + branchName + ' --title "feat(1-1): Initialisation du projet Electron Forge + Vite (Round 9 cleanup)" --body "Story 1.1 finalisation.\n\nRound 9 review issues addressed (3 Medium + 4 Low).\n\n## Description\n- Electron Forge + Vite template init\n- src/main.js, src/preload.js, src/renderer.js\n- Tests with vitest\n- Forge config with fuses (RunAsNode false, asar integrity)\n\n## Tests\n- Lint clean\n- Tests pass"\n4. Update sprint-status.yaml: 1-1 in-progress -> review. Commit et push.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Push + PR', schema: SCHEMA_SHIP });

return { ok: true, pr: ship.prUrl, finalCommit: ship.finalCommit, fixedTotal: high.length + mediumLow.length };