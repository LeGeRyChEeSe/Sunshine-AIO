# BMAD Story Workflow v2 - Design

## Leçon apprise (story 1.2)

Le workflow v1 avait une condition `highCount === 0` qui empêchait le fix loop de s'exécuter
quand il y avait des high issues. C'est l'inverse de ce qu'on veut : on DOIT fixer les high
issues avant de ship.

## Nouveau flow v2

Pour chaque story :

```
Setup (worktree + story file + sprint-status update)
  ↓
Dev (implémentation + tests)
  ↓
Review adversarial 3-perspectives (parallel)
  ↓
Tant que issues.high > 0 :
    Fix high issues
    Re-review ciblé
    Si issues.medium augmentent → continuer
  ↓
Tant que issues.medium > 3 ET rounds < 3 :
    Fix medium issues
    Re-review ciblé
  ↓
Tant que issues.low > 5 ET rounds < 2 :
    Fix low issues (best-effort)
  ↓
Ship (commit + push + PR + sprint-status → review)
  ↓
[humain review le PR et merge → done]
```

## Critères "parfaitement fonctionnel"

Une story passe en `review` (status sprint) seulement si :
- ✅ 0 issue high
- ✅ ≤ 3 issues medium (ou toutes documentées comme "wontfix" avec raison)
- ✅ Lint + tests passent
- ✅ Tous les AC validés
- ✅ Pas de TODO/stub dans le code

## Fichier workflow script

`bmad-story-v2.js` - à créer, paramétrable par story key

## Stories restantes

| Story | Epic | Status cible | Dépendances |
|-------|------|--------------|-------------|
| 1-2 | Infra | en cours fix | 1-1 |
| 1-3 | Infra | ready | 1-1, 1-2 |
| 1-4 | Infra | ready | 1-1 |
| 1-5 | Infra | ready | 1-1 |
| 2-1 | 3D | ready | 1-* |
| 2-2 | 3D | ready | 2-1 |
| 2-3 | 3D | ready | 2-1 |
| 2-4 | 3D | ready | 2-1, 2-2, 2-3 |
| 3-1 | Nav | ready | 2-* |
| 3-2 | Nav | ready | 3-1 |
| 3-3 | Nav | ready | 3-2 |
| 4-1 | Apps | ready | 3-* |
| 4-2 | Apps | ready | 4-1 |
| 4-3 | Apps | ready | 4-1, 5-1 |
| 5-1 | Install | ready | 1-3, 7-1 |
| 5-2 | Install | ready | 5-1 |
| 5-3 | Install | ready | 5-1 |
| 5-4 | Install | ready | 5-1, 5-3 |
| 6-1 | Updates | ready | 5-* |
| 6-2 | Updates | ready | 6-1 |
| 6-3 | Updates | ready | 6-1 |
| 7-1 | Catalog | ready | 1-3 |
| 7-2 | Catalog | ready | 7-1 |
| 7-3 | Catalog | ready | 7-1 |

## Décisions à prendre

Vu l'ampleur (27 stories × tokens), faut-il :
A. Tout faire en un seul orchestrateur (chaque story est un agent)
B. Faire Epic 1 d'abord (5 stories), valider, puis Epic 2 (4), etc.
C. Faire parallèle sur plusieurs stories d'un même epic quand possible

Recommandation : B - Epic 1 d'abord, validation utilisateur, puis scaling.