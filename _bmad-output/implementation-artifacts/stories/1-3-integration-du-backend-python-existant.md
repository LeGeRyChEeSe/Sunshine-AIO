---
story: 1-3-integration-du-backend-python-existant
title: "Story 1.3: Intégration du backend Python existant"
epic: 1
status: ready-for-dev
branch: story/1-3-integration-du-backend-python-existant
worktree: _bmad-output/worktrees/1-3-integration-du-backend-python-existant
source_epic: _bmad-output/planning-artifacts/epics.md#story-13
created: 2026-06-23
---

# Story 1.3: Intégration du backend Python existant

As a user,
I want the existing Python backend to work with the new Electron frontend,
So that I can reuse the existing installation logic.

## Acceptance Criteria

### AC1 — Communication IPC Electron <-> Python

**Given** The Electron app is launched
**When** The frontend tries to communicate with the backend
**Then** The IPC communication between Electron and Python works
**And** Commands can be sent from the renderer to the main process

### AC2 — Commande ping / pong

**Given** IPC communication is established
**When** The frontend sends a "ping" command to the Python backend
**Then** A "pong" response is received

## Notes

- Cette story vise à établir un pont de communication entre le frontend Electron
  (renderer / main process) et le backend Python existant (`src/main.py` et modules `src/misc/`).
- L'IPC doit être bidirectionnel : le renderer envoie des commandes au main process,
  le main process relaie vers Python et retourne la réponse au renderer.
- Le contrat minimum pour valider la story est un échange `ping` -> `pong`
  fonctionnel de bout en bout.
