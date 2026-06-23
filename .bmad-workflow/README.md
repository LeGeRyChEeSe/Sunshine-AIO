# BMAD Story Implementation Workflow

## Vue d'ensemble

Workflow réutilisable qui orchestre pour chaque story BMAD :
1. Création du worktree (git worktree + branche `story/<id>`)
2. Création du fichier de story + mise à jour sprint-status
3. Implémentation par agent Dev (lit architecture/PRD/AC, écrit code + tests)
4. Review adversariale 3-perspectives (correctness / security / quality)
5. Boucle de fix si issues trouvées (jusqu'à "dry" = 2 rounds sans nouveau)
6. Commit + push + ouverture PR
7. Sprint-status mis à jour (`review` → `done`)

## Dépendances entre stories

```
Epic 1 (infra) : 1-1 → 1-2 → 1-3 → 1-4 → 1-5
Epic 2 (3D)    : 1-*   → 2-1 → 2-2 → 2-3 → 2-4
Epic 3 (nav)   : 2-*   → 3-1 → 3-2 → 3-3
Epic 4 (apps)   : 3-* + 5-*  → 4-1 → 4-2 → 4-3
Epic 5 (install): 1-* + 7-*  → 5-1 → 5-2 → 5-3 → 5-4
Epic 6 (updates): 5-*         → 6-1 → 6-2 → 6-3
Epic 7 (catalog): 1-*         → 7-1 → 7-2 → 7-3
```

## Conventions

- **Branche** : `story/<num>-<slug-kebab>`
- **Worktree** : `_bmad-output/worktrees/story-<num>-<slug-kebab>/`
- **Story file** : `_bmad-output/implementation-artifacts/stories/<num>-<slug>.md`
- **Implémentation** : dans `sunshine-aio/` (subfolder Electron)
- **PR title** : `feat(<num>): <titre>`

## Quality gates

Une story passe en `review` puis `done` seulement si :
- ✅ Tous les AC validés par l'agent test
- ✅ `npm run lint` passe
- ✅ `npm test` passe
- ✅ Review adversariale : 0 issue High, ≤2 Medium, ≤4 Low
- ✅ Branche pushée, PR créée sur `bmad` (jamais sur `main`)

## Commandes utiles

```bash
# Voir les worktrees actifs
git worktree list

# Cleanup après merge
git worktree remove _bmad-output/worktrees/story-X-Y

# Sprint status
cat _bmad-output/implementation-artifacts/sprint-status.yaml
```