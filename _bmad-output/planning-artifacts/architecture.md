---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/product-brief-Sunshine-AIO-2026-02-21.md"
  - "_bmad-output/planning-artifacts/ux-design-specification.md"
  - "_bmad-output/project-context.md"
workflowType: 'architecture'
project_name: 'Sunshine-AIO'
user_name: 'Kilian'
date: '2026-02-21'
lastStep: 8
status: 'complete'
completedAt: '2026-02-22'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
- **Interface 3D (FR1-FR4)**: Système solaire 3D procédural avec planètes représentant les catégories d'applications. Le soleil représente les outils core (Sunshine/Apollo, VDD, Playnite).
- **Navigation (FR5-FR7)**: Scroll horizontal entre planètes, clic pour voir les détails, retour à la vue système.
- **Découverte d'apps (FR8-FR11)**: Liste des apps par catégorie, détails, identification des apps installées et mises à jour disponibles.
- **Installation (FR12-FR16)**: Installation 1-clic, désinstallation, progression visuelle, confirmation, réinstallation.
- **Mises à jour (FR17-FR19)**: Notifications, liste des apps avec updates, mise à jour.
- **Gestion d'état (FR20-FR21)**: Persistance de la configuration du système solaire entre sessions.
- **Intégration catalogue (FR22-FR24)**: Récupération du catalogue communautaire, refresh, support hors ligne.
- **Intégration système (FR25-FR28)**: Privilèges admin, registre Windows, notifications système, tray.

**Non-Functional Requirements:**
- **Performance**: 30 FPS minimum sur matériel moyen, chargement < 5 secondes, UI responsive pendant installations
- **Intégration**: Dégradation gracieuse hors ligne (cache), fallback pattern pour téléchargements GitHub
- **Fiabilité**: Logging des erreurs d'installation, sauvegarde d'état avant opérations critiques

### Technical Constraints & Dependencies

- **Plateforme**: Windows 10/11 uniquement (x64)
- **Stack actuel**: Application console Python → Transformation vers Electron + Three.js + Python backend
- **Dépendances système**: Accès registre Windows, services Windows, règles firewall, privilèges admin
- **Contraintes de rendu 3D**: Maintenir 30 FPS, optimiser les textures et géométries

### Cross-Cutting Concerns Identified

1. **Communication IPC Electron↔Python**: Le backend Python existant doit communiquer avec le nouveau frontend Electron. Nécessite un protocole IPC robuste.
2. **Gestion d'état 3D**: Synchronisation entre l'état des installations (Python) et la représentation 3D (Three.js).
3. **Performance de rendu**: Balance entre qualité visuelle et performance (30 FPS target).
4. **Persistance d'état**: Sauvegarde et restauration de l'état du système solaire entre sessions.
5. **Catalogue et offline**: Gestion du cache du catalogue communautaire pour le mode hors ligne.

---

## Starter Template Evaluation

### Primary Technology Domain

**Application Desktop** : Electron + Three.js (frontend) + Python (backend)

Based on project requirements analysis - 3D rendering, rich animations, and real-time interaction requirements.

### Starter Options Considered

**1. Electron Forge + Vite (Recommandé)**
- Starter officiel Electron avec support Vite
- Hot reload rapide pour le développement
- Structure moderne avec ESM
- Compatible avec React et Three.js

**2. electron-vite**
- Alternative populaire à Electron Forge
- Bonne intégration avec React Three Fiber
- Configuration simplifiée

**3. electron-vue ou electron-react-boilerplate**
- Plus anciens, moins de maintenance récente

### Selected Starter: Electron Forge + Vite

**Rationale for Selection:**
- Support officiel Electron avec longue durée de vie
- Excellent support Three.js/react-three-fiber
- Développement rapide avec HMR
- Communauté active et bien documentée

**Initialization Command:**

```bash
npm create electron-app@latest sunshine-aio -- --template=vite
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- JavaScript/TypeScript avec ESM
- Node.js runtime dans le processus renderer

**Build Tooling:**
- Vite pour le développement rapide (HMR)
- electron-builder pour la création d'exécutables Windows

**Project Structure:**
- Separation main process / renderer process
- Preload scripts pour l'IPC sécurisé

**Development Experience:**
- Hot Module Replacement pendant le développement
- Debugging via DevTools Electron

**Note:** Project initialization using this command should be the first implementation story.

---

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- State management for 3D sync
- IPC communication protocol between Electron and Python
- Data persistence format

**Important Decisions (Shape Architecture):**
- 3D library choice (Three.js vs react-three-fiber)
- Component architecture patterns

**Deferred Decisions (Post-MVP):**
- Advanced theming system
- Big Bang and Invasion animations

### Frontend Architecture - State Management

**Decision:** Zustand
**Version:** ^4.5.0 (latest stable)

**Rationale:** Lightweight state management that integrates well with React Three Fiber. Zustand's transient updates are ideal for 3D rendering performance (avoids unnecessary re-renders).

**Affects:** All frontend components, 3D scene synchronization

### IPC Communication - Electron ↔ Python

**Decision:** electron IPC (ipcMain/ipcRenderer)

**Rationale:** Native Electron IPC is sufficient for this use case. The communication pattern is simple (request/response for installation commands). Can upgrade to socket.io if more complex messaging is needed later.

**Affects:** Main process, renderer process, Python backend integration

### Data Persistence

**Decision:** JSON files + electron-store

**Rationale:** Simple and matches existing project patterns. electron-store provides a clean API for persistent data while maintaining compatibility with the existing JSON-based configuration system.

**Affects:** User preferences, world state, installation tracking

### Decision Impact Analysis

**Implementation Sequence:**
1. Initialize Electron project with Vite template
2. Set up IPC communication layer
3. Integrate Python backend
4. Implement Zustand store for state management
5. Build 3D scene with Three.js
6. Connect UI overlays to state

**Cross-Component Dependencies:**
- IPC must be established before Python integration
- Zustand store should be designed before component implementation
- 3D scene depends on state management architecture

---

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 5 areas where AI agents could make different choices

### Naming Patterns

**File Naming Conventions:**
- **React Components:** PascalCase (e.g., `SolarSystem.tsx`, `Planet.tsx`, `PlanetOverlay.tsx`)
- **JavaScript/TypeScript files:** camelCase (e.g., `installApp.ts`, `getPlanetData.ts`)
- **Constants:** SCREAMING_SNAKE_CASE (e.g., `IPC_CHANNELS`, `MAX_PLANETS`)
- **Configuration files:** kebab-case (e.g., `app-config.json`, `theme-settings.json`)

**Code Naming Conventions:**
- **Variables/functions:** camelCase (e.g., `installApp()`, `planetData`)
- **Classes:** PascalCase (e.g., `SolarSystem`, `PlanetManager`)
- **Private members:** Leading underscore (e.g., `_planets`, `_installations`)

**IPC Channel Naming:**
- Format: `domain:action` (e.g., `install:start`, `install:progress`, `catalog:fetch`)
- Use lowercase with colons

### Structure Patterns

**Project Organization:**
- Feature-based organization for components
- Type-based organization for utilities and hooks
- Co-located tests next to components

**Directory Structure:**
```
src/
├── main/                 # Electron main process
│   ├── index.ts
│   ├── ipc/              # IPC handlers
│   └── preload.ts
├── renderer/             # React frontend
│   ├── App.tsx
│   ├── components/       # UI components
│   │   ├── SolarSystem/
│   │   ├── Planet/
│   │   └── Overlay/
│   ├── stores/           # Zustand stores
│   ├── hooks/            # Custom hooks
│   ├── services/         # API/IPC services
│   └── styles/           # CSS/styled components
└── python/               # Python backend (existing)
```

### Communication Patterns

**IPC Communication:**
- Request/response pattern for commands
- Event-based for progress updates
- All payloads in JSON format

**State Management (Zustand):**
- Store naming: `use[Domain]Store` (e.g., `useSolarSystemStore`)
- Actions: imperative verbs (e.g., `setPlanets()`, `addInstallation()`)

### Process Patterns

**Error Handling:**
- All errors logged with context
- User-friendly error messages displayed in UI
- Errors propagated through IPC channels

**Loading States:**
- Local loading states in components
- Global loading indicator for background operations

### Enforcement Guidelines

**All AI Agents MUST:**
- Follow file naming conventions exactly
- Use IPC channels defined in shared constants
- Implement Zustand stores following the pattern
- Keep Python backend interface unchanged

---

## Project Structure & Boundaries

### Complete Project Directory Structure

```
sunshine-aio/
├── package.json
├── vite.config.ts
├── electron-builder.json
├── tsconfig.json
├── .env.example
├── .gitignore
├── README.md
├── src/
│   ├── main/                      # Electron main process
│   │   ├── index.ts              # Entry point
│   │   ├── preload.ts            # Preload script
│   │   └── ipc/
│   │       ├── handlers.ts       # IPC handlers
│   │       └── channels.ts      # Channel constants
│   ├── renderer/                 # React frontend
│   │   ├── index.html
│   │   ├── main.tsx             # React entry
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SolarSystem/
│   │   │   │   ├── SolarSystem.tsx
│   │   │   │   ├── Planet.tsx
│   │   │   │   ├── Sun.tsx
│   │   │   │   ├── Orbit.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Overlay/
│   │   │   │   ├── PlanetOverlay.tsx
│   │   │   │   ├── AppCard.tsx
│   │   │   │   └── AppDetails.tsx
│   │   │   └── UI/
│   │   │       ├── InstallButton.tsx
│   │   │       ├── Toast.tsx
│   │   │       └── LoadingSpinner.tsx
│   │   ├── stores/
│   │   │   ├── useSolarSystemStore.ts
│   │   │   └── useAppStore.ts
│   │   ├── hooks/
│   │   │   ├── useIPC.ts
│   │   │   └── use3DScene.ts
│   │   ├── services/
│   │   │   ├── ipcService.ts
│   │   │   └── catalogService.ts
│   │   └── styles/
│   │       ├── global.css
│   │       └── theme.ts
│   └── python/                    # Python backend (existing)
│       ├── main.py
│       └── misc/                  # Existing Python modules
└── compiler/                      # Existing build scripts
```

### Architectural Boundaries

**IPC Boundaries:**
- Main process ↔ Renderer via preload script (contextBridge)
- Renderer → Python commands via IPC handlers in main process

**Component Boundaries:**
- 3D Scene (Three.js) ↔ React UI via Zustand stores
- Overlay components communicate through shared stores

### Requirements to Structure Mapping

**3D Interface (FR1-FR4):**
- Components: `src/renderer/components/SolarSystem/`
- Stores: `src/renderer/stores/useSolarSystemStore.ts`

**Installation (FR12-FR16):**
- Services: `src/renderer/services/ipcService.ts`
- IPC handlers: `src/main/ipc/handlers.ts`

**Catalog Integration (FR22-FR24):**
- Services: `src/renderer/services/catalogService.ts`

---

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Electron + Vite + React + Three.js + Zustand + IPC - all technologies are compatible
- IPC communication pattern fits the Electron architecture
- electron-store integrates well with JSON-based persistence

**Pattern Consistency:**
- File naming conventions align with structure patterns
- IPC channel naming follows the `domain:action` format
- Zustand store pattern consistent across components

**Structure Alignment:**
- Project structure supports all architectural decisions
- Component boundaries properly defined
- Integration points clearly mapped

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
- Interface 3D (FR1-4): SolarSystem components + Three.js ✅
- Navigation (FR5-7): Planet components + scroll ✅
- App Discovery (FR8-11): Overlay components + AppCard ✅
- Installation (FR12-16): IPC handlers + ipcService ✅
- Updates (FR17-19): State management + notifications ✅
- State Management (FR20-21): electron-store + Zustand ✅
- Catalog (FR22-24): catalogService ✅
- System Integration (FR25-28): IPC handlers + Python backend ✅

**Non-Functional Requirements Coverage:**
- Performance (30 FPS): Three.js optimization patterns ✅
- Offline support: Catalog caching strategy ✅
- Reliability: Error handling patterns ✅

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical decisions documented with versions
- Technology stack fully specified
- Integration patterns defined

**Structure Completeness:**
- Complete directory structure defined
- Component boundaries established
- Integration points mapped

**Pattern Completeness:**
- Naming conventions comprehensive
- Communication patterns fully specified
- Process patterns (error handling, loading) documented

### Gap Analysis Results

**Critical Gaps:** None
**Important Gaps:** Exact Three.js version to verify during implementation
**Nice-to-Have:** Advanced theming system (deferred to post-MVP)

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clear separation between Electron main/renderer processes
- Robust IPC communication pattern defined
- Comprehensive state management strategy
- All functional requirements architecturally supported

**Areas for Future Enhancement:**
- Advanced theming system (post-MVP)
- Big Bang animation implementation
- Invasion/Devastation animations

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
```bash
npm create electron-app@latest sunshine-aio -- --template=vite
```

---

