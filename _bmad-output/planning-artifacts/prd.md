---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - "_bmad-output/brainstorming/brainstorming-session-2026-02-20.md"
  - "_bmad-output/project-context.md"
  - "_bmad-output/planning-artifacts/product-brief-Sunshine-AIO-2026-02-21.md"
workflowType: 'prd'
classification:
  projectType: desktop_app
  domain: general
  complexity: low
  projectContext: brownfield
---

# Product Requirements Document - Sunshine-AIO

**Author:** Kilian
**Date:** 2026-02-21

## Executive Summary

Sunshine-AIO is a Windows desktop application that provides a unique 3D solar system interface for discovering and installing game streaming tools and community apps. The application replaces the existing console-based menu with an immersive planetary navigation system where planets represent app categories and apps are discovered through an interactive 3D experience.

**Target Users:** Gamers wanting to set up game streaming (Sunshine/VDD/Playnite)

**Key Differentiator:** First 3D narrative installer with procedural solar system visualization

## Success Criteria

### User Success

- User can navigate the 3D solar system interface smoothly
- User can discover and install community apps through the planetary interface
- User receives notifications when app updates are available

### Business Success

- Increase user engagement through unique visual experience
- Simplify community app discovery and installation

### Technical Success

- 3D solar system renders at stable framerate
- Installation success rate maintained or improved
- Cross-component communication (Electron ↔ Python) works reliably

### Measurable Outcomes

- Initial load time under 5 seconds
- Successful installations complete without errors
- UI remains responsive during background installations

## Product Scope

### MVP - Minimum Viable Product

- 3D solar system with procedural planet generation
- Basic planet navigation (horizontal scroll)
- Click on planet → app details overlay
- Install/uninstall community apps
- Electron + Python backend integration

### Growth Features (Post-MVP)

- "Big Bang" intro animation during first install
- Invasion/devastation animations
- Notification system for updates
- World state persistence
- Regenerate world option

### Vision (Future)

- Cross-platform support (future consideration)
- Advanced animations and visual effects
- Full community catalog integration

## User Journeys

### Primary User - Initial Setup (Happy Path)

**User:** Gamer wanting to set up game streaming

**Journey:**
1. Opens Sunshine-AIO for first time
2. Sees black screen with "Every great stream starts in the dark. Let's bring the light."
3. Clicks anywhere to trigger "Big Bang" animation
4. Watches as sun forms and core tools install (Sunshine/Apollo, VDD, Playnite)
5. Planets appear as each tool completes installation
6. System solar view displays with all installed planets in color, community planets grayed
7. Can scroll horizontally to explore all category planets

### Primary User - Discover and Install Community App

**User:** Gamer exploring community apps

**Journey:**
1. Opens Sunshine-AIO (subsequent use)
2. Navigates solar system via horizontal scroll
3. Notices glowing/pulsing planet (indicates available apps)
4. Clicks on planet → overlay "card" appears
5. Views app details: screenshots, description, version
6. Clicks "Install" button
7. Sees invasion animation on planet region
8. App installs in background
9. Planet updates to show app is now installed

### Primary User - Update Check

**User:** Gamer checking for updates

**Journey:**
1. Opens Sunshine-AIO
2. Notices planet has pulsing glow (update indicator)
3. Clicks on planet to see which apps have updates
4. Views update details in overlay
5. Clicks "Update" on specific apps
6. Notification received when update completes

### Secondary User - Maintenance Mode

**User:** User managing installed apps

**Journey:**
1. Opens Sunshine-AIO
2. Navigates to installed planet
3. Views list of installed apps
4. Can uninstall apps (sees devastation animation)
5. Can reinstall previously uninstalled apps

### Journey Requirements Summary

- **Onboarding:** First-run Big Bang animation with progressive sun/planet formation
- **Navigation:** Horizontal scroll between planets, click to focus
- **Discovery:** Planet overlay with app cards (translucent design)
- **Installation:** Invasion animation, progress indication, success feedback
- **Uninstallation:** Devastation animation, confirmation, cleanup
- **Updates:** System notification, planet pulse indicator, in-app update flow
- **State Persistence:** World state saved and restored on app restart

## Innovation & Novel Patterns

### Detected Innovation Areas

- **Système solaire 3D procédural** - Interface unique jamais vue dans un installateur
- **Métaphore géographique** - Catégories = planètes, apps = pays/continents
- **Animation Big Bang narrative** - Intro immersive au premier lancement
- **Invasion/Dévastation** - Animations au lieu de barres de progression
- **Planètes pulsantes** - Indicateur visuel pour apps communautaires et updates

### Market Context

- Marché des installateurs gaming: très peu d'innovation UI depuis 10 ans
- Aucune solutionexistante avec interface 3D narrative
- Potentiel de différenciation forte

### Validation Approach

- Alpha test avec gamers pour valider l'intuitivité de la navigation
- Mesure du temps de découverte des apps communautaires

## Desktop Application Specific Requirements

### Platform Support

- **Primary Platform:** Windows 10/11 only (initial release)
- **Architecture:** x64
- **Future:** Cross-platform support considered in Vision phase

### System Integration

- **Admin Privileges:** Required for VDD and system-level installations
- **Registry:** Windows registry access for component tracking
- **Services:** Windows services management for background operations
- **Firewall:** Firewall rule management for network features
- **Notifications:** System tray and Windows notifications

### Update Strategy

- **App Updates:** Self-update mechanism for Sunshine-AIO core
- **Community App Updates:** Check against sunshine-aio-library catalog
- **Notification:** System notification when updates available
- **Background Service:** Lightweight service for update checking

### Offline Capabilities

- **Full Offline Support:** App works without internet
- **Catalog Sync:** Fetch community app list on startup or on-demand refresh
- **Downloads:** Apps downloaded from GitHub or other sources when online

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Experience-focused MVP - deliver unique 3D solar system UI that proves the concept
**Resource Requirements:** 1 developer with Three.js/Electron/Python skills

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Initial setup with simplified onboarding
- Navigate solar system
- Discover and install community apps
- View app details

**Must-Have Capabilities:**
- Electron + Three.js frontend
- Python backend via IPC
- 3D solar system with procedural planets
- Horizontal scroll navigation
- Planet click → app overlay
- Install/uninstall community apps
- sunshine-aio-library integration

### Post-MVP Features

**Phase 2 (Growth):**
- Big Bang intro animation
- Invasion/devastation animations
- System notifications for updates
- World state persistence
- Regenerate world option
- List view alternative

**Phase 3 (Expansion):**
- Cross-platform (Mac/Linux)
- Advanced visual effects
- Full community catalog
- Multi-language support

### Risk Mitigation Strategy

**Technical Risks:** Three.js complexity - start with basic rendering, add effects incrementally
**Market Risks:** Unique UI differentiation validates concept quickly
**Resource Risks:** Single developer can deliver MVP with focused scope

## Functional Requirements

### 3D Interface

- FR1: User can view a 3D solar system with procedurally generated planets
- FR2: User can see the sun as the central element representing core tools
- FR3: User can see planets representing app categories
- FR4: User can distinguish between installed apps (colored) and available apps (grayed)

### Navigation

- FR5: User can scroll horizontally between planets
- FR6: User can click on a planet to focus and view its details
- FR7: User can return to the solar system overview from a planet view

### App Discovery

- FR8: User can view a list of apps within a category (planet)
- FR9: User can view app details including description, version, and screenshots
- FR10: User can identify which apps are already installed
- FR11: User can identify which apps have updates available

### Installation

- FR12: User can install community apps from the interface
- FR13: User can uninstall installed apps
- FR14: User can view installation progress
- FR15: User receives confirmation when installation completes
- FR16: User can reinstall previously uninstalled apps

### Updates

- FR17: User receives notification when app updates are available
- FR18: User can view list of apps with available updates
- FR19: User can update apps to newer versions

### State Management

- FR20: User's world configuration persists between app sessions
- FR21: User can regenerate the procedural world (optional feature)

### Catalog Integration

- FR22: App can fetch community app catalog from sunshine-aio-library
- FR23: App can refresh catalog on demand
- FR24: App can work offline using cached catalog data

### System Integration

- FR25: App requires Windows admin privileges for system installations
- FR26: App can access Windows registry for component tracking
- FR27: App can display Windows system notifications
- FR28: App can run in system tray

## Non-Functional Requirements

### Performance

- NFR1: 3D solar system renders at minimum 30 FPS on average hardware
- NFR2: Initial app load time under 5 seconds
- NFR3: UI remains responsive during background installations
- NFR4: Smooth horizontal scrolling between planets

### Integration

- NFR5: Catalog sync fails gracefully when offline (uses cached data)
- NFR6: GitHub downloads include fallback pattern matching for asset names

### Reliability

- NFR7: Installation failures logged with clear error messages
- NFR8: App state saved before critical operations

