---
story_id: 1-4-configuration-des-privileges-admin-et-du-system-tray
epic: 1
title: Configuration des privilèges admin et du system tray
status: ready-for-dev
branch: story/1-4-configuration-des-privileges-admin-et-du-system-tray
created: 2026-06-23
---

# Story 1.4: Configuration des privilèges admin et du system tray

## User Story

As a user,
I want the application to request admin privileges when needed and be minimized to the system tray,
So that I have a native Windows experience.

## Acceptance Criteria

**Given** The application is launched
**When** The user launches the application
**Then** The application can request administrator privileges if needed
**And** The application can be minimized to the system tray
**And** Clicking the tray icon restores the window

**Given** The application is in the tray
**When** The user right-clicks the tray icon
**Then** A context menu displays "Open" and "Quit"

## Notes

- Source: `_bmad-output/planning-artifacts/epics.md` (Story 1.4)
- Epic 1: Setup & Infrastructure de l'application Electron
- This story is part of the Electron app transformation of Sunshine-AIO
