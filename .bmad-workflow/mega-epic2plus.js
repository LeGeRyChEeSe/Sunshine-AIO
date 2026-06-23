// Mega workflow Epic 2-7 - process stories sequentially
// Each story gets full BMAD cycle: setup -> dev -> review -> fix -> ship

export const meta = {
  name: 'bmad-mega-epic2plus',
  description: 'Process Epic 2-7 stories sequentially',
  phases: [
    { title: 'Story 2-1 Three.js+Zustand' },
    { title: 'Story 2-2 Sun component' },
    { title: 'Story 2-3 Planet component' },
    { title: 'Story 2-4 State persistence' },
    { title: 'Story 3-1 Horizontal scroll' },
    { title: 'Story 3-2 Planet focus click' },
    { title: 'Story 3-3 Back to overview' },
    { title: 'Story 4-1 App list by category' },
    { title: 'Story 4-2 App details' },
    { title: 'Story 4-3 Installed/updates identification' },
    { title: 'Story 5-1 Install app' },
    { title: 'Story 5-2 Install progress viz' },
    { title: 'Story 5-3 Uninstall' },
    { title: 'Story 5-4 Reinstall' },
    { title: 'Story 6-1 Update notifications' },
    { title: 'Story 6-2 Updates list' },
    { title: 'Story 6-3 Update apps' },
    { title: 'Story 7-1 Catalog fetch' },
    { title: 'Story 7-2 Catalog refresh' },
    { title: 'Story 7-3 Offline cache' },
  ],
};

const repoRoot = 'D:/Documents/Programmation/Projets/Sunshine-AIO';

const STORIES = [
  {
    key: '2-1-configuration-de-three-js-et-zustand',
    title: 'Configuration Three.js et Zustand',
    ac: ['Three.js renders in app window', 'Zustand stores manage app state', 'Canvas 3D displays content', 'FPS monitored and logged'],
    dev: `1. npm install three zustand
2. Creer sunshine-aio/src/three/setup.js: WebGL renderer, scene, PerspectiveCamera, animation loop, resize handler, FPS monitoring via logger, cleanup dispose
3. Creer sunshine-aio/src/state/store.js: Zustand store (worldState, installState, navigationState), localStorage persistence, actions: setPlanetStatus, addInstalledApp, setCurrentView
4. Modifier sunshine-aio/src/renderer.js: init Three.js scene, hook Zustand, FPS overlay
5. Tests: three/setup.test.js (renderer creation, resize, FPS, cleanup), state/store.test.js (initial state, actions, persistence)
6. Verify: npm run lint && npm test
7. Commit: feat(2-1): Three.js + Zustand setup with FPS monitoring`,
    files: ['sunshine-aio/src/three/setup.js (new)', 'sunshine-aio/src/state/store.js (new)', 'sunshine-aio/src/three/setup.test.js (new)', 'sunshine-aio/src/state/store.test.js (new)', 'sunshine-aio/src/renderer.js (modify)']
  },
  {
    key: '2-2-creation-du-composant-sun-soleil',
    title: 'Creation composant Sun',
    ac: ['Sun with orange/yellow glow at center', 'Pulsing animation', 'Core tools indicators (Sunshine, VDD, Playnite)'],
    dev: `1. Creer sunshine-aio/src/three/sun.js: SphereGeometry, MeshStandardMaterial emissive orange/yellow, glow via SpriteLayer ou halo SphereGeometry, pulsing via sin(time) scale, 3 satellites pour core tools
2. Tests: three/sun.test.js (creation, pulsation, setInstalledTools, cleanup dispose)
3. Modifier three/setup.js: add sun to scene, wire avec Zustand
4. Modifier state/store.js: slice coreTools
5. Verify: npm run lint && npm test
6. Commit: feat(2-2): Sun component with glow and core tools`,
    files: ['sunshine-aio/src/three/sun.js (new)', 'sunshine-aio/src/three/sun.test.js (new)', 'sunshine-aio/src/three/setup.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '2-3-creation-du-composant-planet-planetes',
    title: 'Creation composant Planet',
    ac: ['Planets in orbital positions around sun', 'Unique procedural appearance per planet', 'Color reflects installed status (grayed vs colored)'],
    dev: `1. Creer sunshine-aio/src/three/planet.js: SphereGeometry, procedural noise texture, orbital position, color selon installed, animation rotation+revolution
2. Creer sunshine-aio/src/three/orbits.js: visualise orbites avec LineDashedMaterial
3. Creer sunshine-aio/src/three/planetFactory.js: createPlanetsForCategories(categories) genere N planets
4. Modifier three/setup.js: utilise planetFactory
5. Modifier state/store.js: categories slice
6. Tests: three/planet.test.js, three/planetFactory.test.js
7. Verify: npm run lint && npm test
8. Commit: feat(2-3): Planet component with orbital positions`,
    files: ['sunshine-aio/src/three/planet.js (new)', 'sunshine-aio/src/three/orbits.js (new)', 'sunshine-aio/src/three/planetFactory.js (new)', 'sunshine-aio/src/three/planet.test.js (new)', 'sunshine-aio/src/three/planetFactory.test.js (new)']
  },
  {
    key: '2-4-implementation-de-la-persistance-d-etat',
    title: 'Persistance d etat',
    ac: ['World config persistante entre sessions', 'Install state saved', 'Au restart, planet colors refletent installed apps', 'Option regenerate world preserve apps'],
    dev: `1. npm install electron-store
2. Creer sunshine-aio/src/state/persistence.js: wrapper electron-store, keys worldConfig/installedApps/navigationHistory, getWorldConfig/setWorldConfig, regenerateWorld preserve apps
3. Modifier state/store.js: hydrate depuis disk au boot, save middleware avec throttle/debounce
4. Modifier three/planetFactory.js: utilise seed depuis worldConfig.seed
5. Modifier renderer.js: action "Regenerate World" avec confirmation
6. Tests: state/persistence.test.js (save/load, regenerate, corruption recovery)
7. Verify: npm run lint && npm test
8. Commit: feat(2-4): persistent state with world regen option`,
    files: ['sunshine-aio/src/state/persistence.js (new)', 'sunshine-aio/src/state/persistence.test.js (new)', 'sunshine-aio/src/state/store.js (modify)', 'sunshine-aio/src/three/planetFactory.js (modify)', 'sunshine-aio/src/renderer.js (modify)']
  },
  {
    key: '3-1-implementation-du-scroll-horizontal',
    title: 'Scroll horizontal entre planetes',
    ac: ['Scroll horizontal fonctionne', 'Camera moves smoothly between planets', 'Inertia pour natural feel', 'Wrap or stop at boundary'],
    dev: `1. Creer sunshine-aio/src/three/scroll.js: HorizontalScrollController, mouse wheel + drag, camera interpolation, inertia, boundary check
2. Modifier three/setup.js: wire scroll controller
3. Tests: three/scroll.test.js
4. Verify: npm run lint && npm test
5. Commit: feat(3-1): horizontal scroll with inertia`,
    files: ['sunshine-aio/src/three/scroll.js (new)', 'sunshine-aio/src/three/scroll.test.js (new)', 'sunshine-aio/src/three/setup.js (modify)']
  },
  {
    key: '3-2-clic-sur-planete-et-focalisation',
    title: 'Clic sur planete et focalisation',
    ac: ['Click planet focuses', 'Camera zooms in', 'Overlay avec liste apps'],
    dev: `1. Creer sunshine-aio/src/three/raycaster.js: planet click detection via Raycaster
2. Creer sunshine-aio/src/ui/overlay.js: overlay component (planet details)
3. Modifier three/setup.js: raycaster + camera focus animation
4. Modifier state/store.js: currentPlanet slice
5. Tests: three/raycaster.test.js, ui/overlay.test.js
6. Verify: npm run lint && npm test
7. Commit: feat(3-2): planet click focus with overlay`,
    files: ['sunshine-aio/src/three/raycaster.js (new)', 'sunshine-aio/src/ui/overlay.js (new)', 'sunshine-aio/src/three/setup.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '3-3-retour-a-la-vue-systeme-solaire',
    title: 'Retour vue systeme solaire',
    ac: ['Click back button ou outside overlay closes', 'Escape key closes overlay', 'Returns to solar system overview'],
    dev: `1. Modifier sunshine-aio/src/ui/overlay.js: back button, click outside detection, escape key handler
2. Modifier three/setup.js: camera zoom out animation
3. Modifier state/store.js: setCurrentView(null)
4. Tests: ui/overlay.test.js (escape, back button, click outside)
5. Verify: npm run lint && npm test
6. Commit: feat(3-3): back to solar system overview`,
    files: ['sunshine-aio/src/ui/overlay.js (modify)', 'sunshine-aio/src/three/setup.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '4-1-affichage-de-la-liste-des-applications-par-categorie',
    title: 'Liste apps par categorie',
    ac: ['Liste apps affichee dans overlay', 'Each app shows name + installation status', 'List scrolls smoothly'],
    dev: `1. Creer sunshine-aio/src/ui/appList.js: liste apps avec scroll, badges installed
2. Modifier sunshine-aio/src/ui/overlay.js: utilise appList
3. Modifier state/store.js: apps slice (avec installed status)
4. Tests: ui/appList.test.js
5. Verify: npm run lint && npm test
6. Commit: feat(4-1): app list per category in overlay`,
    files: ['sunshine-aio/src/ui/appList.js (new)', 'sunshine-aio/src/ui/overlay.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '4-2-affichage-des-details-d-une-application',
    title: 'Details d une application',
    ac: ['App details avec description, version, screenshots', 'Back button to app list'],
    dev: `1. Creer sunshine-aio/src/ui/appDetails.js: details view (description, version, screenshots gallery)
2. Modifier sunshine-aio/src/ui/overlay.js: navigation appList <-> appDetails
3. Modifier state/store.js: currentApp slice
4. Tests: ui/appDetails.test.js
5. Verify: npm run lint && npm test
6. Commit: feat(4-2): app details view with screenshots`,
    files: ['sunshine-aio/src/ui/appDetails.js (new)', 'sunshine-aio/src/ui/overlay.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '4-3-identification-des-apps-installees-et-mises-a-jour',
    title: 'Identification apps installees et updates',
    ac: ['Installed apps shows "Installed" badge', 'Planet color reflects installation status', 'Apps with update shows indicator', 'Planet pulses/glows for updates'],
    dev: `1. Modifier sunshine-aio/src/ui/appList.js: badges installed + update
2. Modifier sunshine-aio/src/three/planet.js: pulse animation si updates dispo, color change selon installed
3. Modifier state/store.js: updateAvailable flag per app, update pulse on planet
4. Tests: ui/appList.test.js, three/planet.test.js
5. Verify: npm run lint && npm test
6. Commit: feat(4-3): installed + updates identification with visual indicators`,
    files: ['sunshine-aio/src/ui/appList.js (modify)', 'sunshine-aio/src/three/planet.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '5-1-installation-d-une-application',
    title: 'Installation d une app',
    ac: ['Click Install button starts installation', 'Button shows loading state', 'Success notification on complete', 'Planet color updates', 'Retry on error'],
    dev: `1. Creer sunshine-aio/src/services/installer.js: interface avec pythonBridge (depuis story 1-3) pour installer une app
2. Modifier sunshine-aio/src/ui/appDetails.js: Install button + handler
3. Modifier state/store.js: installState (pending, success, error), retry action
4. Hook avec notifications.js (story 1-5) pour success/error notifications
5. Tests: services/installer.test.js, ui/appDetails.test.js
6. Verify: npm run lint && npm test
7. Commit: feat(5-1): install app with notification`,
    files: ['sunshine-aio/src/services/installer.js (new)', 'sunshine-aio/src/ui/appDetails.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '5-2-visualisation-de-la-progression-d-installation',
    title: 'Visualisation progression installation',
    ac: ['Progress indication (percentage ou animation)', 'UI responsive pendant install'],
    dev: `1. Modifier sunshine-aio/src/ui/appDetails.js: progress bar, animation spinner
2. Modifier sunshine-aio/src/services/installer.js: emit progress events (si pythonBridge supporte, sinon poll)
3. Modifier state/store.js: installProgress slice
4. Tests: ui/appDetails.test.js (progress rendering)
5. Verify: npm run lint && npm test
6. Commit: feat(5-2): install progress visualization`,
    files: ['sunshine-aio/src/ui/appDetails.js (modify)', 'sunshine-aio/src/services/installer.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '5-3-desinstallation-d-une-application',
    title: 'Desinstallation',
    ac: ['Click Uninstall shows confirmation dialog', 'Confirm starts uninstall', 'App removed from system', 'Success notification', 'Planet color updates'],
    dev: `1. Creer sunshine-aio/src/services/uninstaller.js: interface pythonBridge pour uninstall
2. Modifier sunshine-aio/src/ui/appDetails.js: Uninstall button + confirmation dialog + handler
3. Modifier state/store.js: removeInstalledApp action
4. Hook notifications (story 1-5)
5. Tests: services/uninstaller.test.js, ui/appDetails.test.js
6. Verify: npm run lint && npm test
7. Commit: feat(5-3): uninstall app with confirmation`,
    files: ['sunshine-aio/src/services/uninstaller.js (new)', 'sunshine-aio/src/ui/appDetails.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '5-4-reinstallation-d-une-application',
    title: 'Reinstallation',
    ac: ['Previously uninstalled app shows Install button', 'Reinstall process same as initial install'],
    dev: `1. Modifier sunshine-aio/src/ui/appDetails.js: Install button always shown (peu importe installed status)
2. Modifier state/store.js: allow addInstalledApp for previously uninstalled apps
3. Tests: ui/appDetails.test.js
4. Verify: npm run lint && npm test
5. Commit: feat(5-4): reinstall support`,
    files: ['sunshine-aio/src/ui/appDetails.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '6-1-notification-des-mises-a-jour-disponibles',
    title: 'Notification updates disponibles',
    ac: ['App checks for updates', 'Notification if updates available', 'Planets with updates pulse/glow', 'Click notification opens app'],
    dev: `1. Creer sunshine-aio/src/services/updateChecker.js: poll github releases or catalog for updates
2. Hook avec notifications.js (story 1-5) pour notifyUpdateAvailable
3. Modifier state/store.js: updateAvailable per app, planet pulse trigger
4. Tests: services/updateChecker.test.js
5. Verify: npm run lint && npm test
6. Commit: feat(6-1): update notifications with planet pulse`,
    files: ['sunshine-aio/src/services/updateChecker.js (new)', 'sunshine-aio/src/services/updateChecker.test.js (new)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '6-2-liste-des-apps-avec-mises-a-jour',
    title: 'Liste apps avec updates',
    ac: ['Planet overlay highlights apps with updates', 'Current version + new version shown'],
    dev: `1. Modifier sunshine-aio/src/ui/appList.js: highlight apps with update, show current + new version
2. Modifier state/store.js: updateVersions per app
3. Tests: ui/appList.test.js
4. Verify: npm run lint && npm test
5. Commit: feat(6-2): apps with updates highlighted`,
    files: ['sunshine-aio/src/ui/appList.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '6-3-mise-a-jour-des-applications',
    title: 'Mise a jour des apps',
    ac: ['Click Update starts update', 'Progress shown', 'Success notification', 'App shows new version'],
    dev: `1. Creer sunshine-aio/src/services/updater.js: interface pythonBridge pour update
2. Modifier sunshine-aio/src/ui/appDetails.js: Update button + handler + progress
3. Modifier state/store.js: updateProgress slice, updateAppVersion action
4. Hook notifications
5. Tests: services/updater.test.js
6. Verify: npm run lint && npm test
7. Commit: feat(6-3): update apps with progress`,
    files: ['sunshine-aio/src/services/updater.js (new)', 'sunshine-aio/src/services/updater.test.js (new)', 'sunshine-aio/src/ui/appDetails.js (modify)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '7-1-recuperation-du-catalogue-communautaire',
    title: 'Recuperation catalogue communautaire',
    ac: ['App fetches catalog from source on start', 'Apps loaded in local state', 'Falls back to cache on network error', 'User not blocked'],
    dev: `1. Creer sunshine-aio/src/services/catalogService.js: fetch catalog from GitHub raw URL, parse JSON, fallback to cache
2. Hook avec state/store.js: catalog slice
3. Tests: services/catalogService.test.js (mock fetch, cache fallback)
4. Verify: npm run lint && npm test
5. Commit: feat(7-1): fetch community catalog with cache fallback`,
    files: ['sunshine-aio/src/services/catalogService.js (new)', 'sunshine-aio/src/services/catalogService.test.js (new)', 'sunshine-aio/src/state/store.js (modify)']
  },
  {
    key: '7-2-refresh-du-catalogue-a-la-demande',
    title: 'Refresh catalogue a la demande',
    ac: ['Click Refresh button', 'App fetches latest catalog', 'App list updates'],
    dev: `1. Modifier sunshine-aio/src/services/catalogService.js: refresh() method
2. Modifier sunshine-aio/src/ui/: Refresh button (settings menu)
3. Tests: services/catalogService.test.js
4. Verify: npm run lint && npm test
5. Commit: feat(7-2): on-demand catalog refresh`,
    files: ['sunshine-aio/src/services/catalogService.js (modify)', 'sunshine-aio/src/ui/settings.js (modify or new)']
  },
  {
    key: '7-3-support-hors-ligne-avec-cache',
    title: 'Support offline avec cache',
    ac: ['Offline launch uses cached catalog', 'All previously available apps visible', 'Install tries fallback patterns', 'Clear error if all sources fail'],
    dev: `1. Modifier sunshine-aio/src/services/catalogService.js: check navigator.onLine, load cache if offline
2. Modifier services/installer.js: fallback patterns for download URLs
3. Tests: catalogService.test.js (offline scenario), installer.test.js (fallback patterns)
4. Verify: npm run lint && npm test
5. Commit: feat(7-3): offline cache support`,
    files: ['sunshine-aio/src/services/catalogService.js (modify)', 'sunshine-aio/src/services/installer.js (modify)']
  },
];

const SCHEMA_SETUP = { type: 'object', properties: { worktreePath: { type: 'string' }, branchName: { type: 'string' }, status: { type: 'string', enum: ['ready', 'error'] }, error: { type: 'string' } }, required: ['worktreePath', 'branchName', 'status'] };
const SCHEMA_DEV = { type: 'object', properties: { filesChanged: { type: 'array', items: { type: 'string' } }, testsAdded: { type: 'array', items: { type: 'string' } }, lintPassed: { type: 'boolean' }, testsPassed: { type: 'boolean' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] }, blocker: { type: 'string' } }, required: ['filesChanged', 'lintPassed', 'testsPassed', 'commitSha', 'status'] };
const SCHEMA_REVIEW = { type: 'object', properties: { issues: { type: 'array', items: { type: 'object', properties: { file: { type: 'string' }, line: { type: 'number' }, severity: { type: 'string', enum: ['high', 'medium', 'low'] }, description: { type: 'string' }, fix: { type: 'string' } }, required: ['file', 'severity', 'description'] } }, verdict: { type: 'string', enum: ['pass', 'fail'] } }, required: ['issues', 'verdict'] };
const SCHEMA_FIX = { type: 'object', properties: { fixedCount: { type: 'number' }, remainingCount: { type: 'number' }, commitSha: { type: 'string' }, status: { type: 'string', enum: ['ok', 'blocked'] } }, required: ['fixedCount', 'remainingCount', 'commitSha', 'status'] };
const SCHEMA_SHIP = { type: 'object', properties: { prUrl: { type: 'string' }, finalCommit: { type: 'string' }, status: { type: 'string', enum: ['ok', 'pushed-no-pr', 'blocked'] } }, required: ['finalCommit', 'status'] };

const STORY_RESULTS = [];

for (let i = 0; i < STORIES.length; i++) {
  const story = STORIES[i];
  const branchName = 'story/' + story.key;
  const worktreePath = repoRoot + '/_bmad-output/worktrees/' + story.key;
  const storyFileRel = '_bmad-output/implementation-artifacts/stories/' + story.key + '.md';

  phase('Story ' + story.key + ' - ' + story.title);

  const setup = await agent('Agent BMAD Setup. Repo: ' + repoRoot + '.\n\nETAPES:\n1. git worktree add ' + worktreePath + ' -b ' + branchName + ' bmad (si existe, remove --force)\n2. Creer ' + worktreePath + '/' + storyFileRel + ' avec frontmatter + AC depuis epics.md section Story ' + story.key + ' (' + story.title + ')\n3. cd ' + worktreePath + ' && git add -A && git commit -m "chore(story-' + story.key + '): setup worktree and story file"\n4. Update bmad sprint-status.yaml: ' + story.key + ' backlog -> in-progress (commit on bmad branch)\n5. Retourne: { worktreePath, branchName, status }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_SETUP });
  if (setup.status !== 'ready') {
    STORY_RESULTS.push({ story: story.key, status: 'setup-failed', error: setup.error });
    continue;
  }
  log('Setup OK: ' + worktreePath);

  const dev = await agent('Agent BMAD Dev. Working dir: ' + worktreePath + '/sunshine-aio. Branch: ' + branchName + '.\n\nSTORY ' + story.key + ': ' + story.title + '.\n\nAC:\n' + story.ac.map(function(b) { return '- ' + b; }).join('\n') + '\n\nETAPES:\n' + story.dev + '\n\nVerifier: cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test\n\nRetourne: { filesChanged, testsAdded, lintPassed, testsPassed, commitSha, status }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_DEV });
  if (dev.status !== 'ok') {
    STORY_RESULTS.push({ story: story.key, status: 'dev-failed', blocker: dev.blocker });
    continue;
  }
  log('Dev OK: ' + dev.filesChanged.length + ' files');

  const reviews = await parallel([
    () => agent('CORRECTNESS reviewer pour story ' + story.key + ' (' + story.title + ') dans ' + worktreePath + '/sunshine-aio. Verifie les AC: ' + story.ac.join(', ') + '. Sois strict sur les edge cases. Schema: { issues: [{file, line, severity, description, fix}], verdict }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_REVIEW }),
    () => agent('SECURITY reviewer pour story ' + story.key + ' dans ' + worktreePath + '/sunshine-aio. Verifie: contextIsolation, channel whitelist, input validation, file path safety, pas d eval. Schema: { issues, verdict }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_REVIEW }),
    () => agent('MAINTAINABILITY reviewer pour story ' + story.key + ' dans ' + worktreePath + '/sunshine-aio. Verifie: code structure, JSDoc, tests utiles (pas mock-only), conventions. Schema: { issues, verdict }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_REVIEW }),
  ]);

  const allIssues = reviews.filter(Boolean).flatMap(function(r) { return r.issues || []; });
  let currentHigh = allIssues.filter(function(i) { return i.severity === 'high'; });
  let currentMedium = allIssues.filter(function(i) { return i.severity === 'medium'; });
  log('Review: ' + currentHigh.length + ' high + ' + currentMedium.length + ' medium');

  let highRounds = 0;
  while (currentHigh.length > 0 && highRounds < 3) {
    highRounds++;
    const fix = await agent('Fix HIGH dans ' + worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentHigh, null, 2) + '. Commit: "fix(' + story.key + '): round ' + highRounds + ' - high". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_FIX });
    if (fix.status !== 'ok') break;
    const reReview = await agent('Re-review HIGH. Schema: { issues, verdict }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_REVIEW });
    const newHigh = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'high'; });
    if (newHigh.length >= currentHigh.length) break;
    currentHigh = newHigh;
  }

  let mediumRounds = 0;
  while (currentMedium.length > 0 && mediumRounds < 2) {
    mediumRounds++;
    const fix = await agent('Fix MEDIUM dans ' + worktreePath + '/sunshine-aio. Issues: ' + JSON.stringify(currentMedium, null, 2) + '. Commit: "fix(' + story.key + '): round ' + mediumRounds + ' - medium". Retourne: { fixedCount, remainingCount, commitSha, status }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_FIX });
    if (fix.status !== 'ok') break;
    const reReview = await agent('Re-review MEDIUM. Schema: { issues, verdict }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_REVIEW });
    const newMed = (reReview && reReview.issues || []).filter(function(i) { return i.severity === 'medium'; });
    if (newMed.length >= currentMedium.length) break;
    currentMedium = newMed;
  }

  const ship = await agent('Ship story ' + story.key + '.\n1. cd ' + worktreePath + '/sunshine-aio && npm run lint && npm test\n2. cd ' + worktreePath + ' && git push origin ' + branchName + '\n3. gh pr create --base bmad --head ' + branchName + ' --title "feat(' + story.key + '): ' + story.title + '" --body "Story ' + story.key + '. Tests: ' + dev.testsAdded.length + '. ' + currentHigh.length + ' high, ' + currentMedium.length + ' medium restants."\n4. Update sprint-status.yaml: ' + story.key + ' in-progress -> review. Commit et push.\n5. Retourne: { prUrl, finalCommit, status }', { phase: 'Story ' + story.key + ' - ' + story.title, schema: SCHEMA_SHIP });

  STORY_RESULTS.push({
    story: story.key,
    title: story.title,
    status: ship.status,
    prUrl: ship.prUrl,
    finalCommit: ship.finalCommit,
    highRemaining: currentHigh.length,
    mediumRemaining: currentMedium.length,
    testsAdded: dev.testsAdded.length,
  });
}

return {
  totalStories: STORIES.length,
  results: STORY_RESULTS,
};