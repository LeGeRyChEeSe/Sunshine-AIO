---
story_key: 1-2-configuration-du-logging-et-gestion-des-erreurs
title: Configuration du logging et gestion des erreurs
status: review
epic: 1
---

# Story 1.2: Configuration du logging et gestion des erreurs

As a user,
I want errors to be logged,
So that technical issues can be diagnosed.

## Acceptance Criteria

**Given** The application is running
**When** An unhandled error occurs
**Then** The error is logged to a log file
**And** A user-friendly error message is displayed to the user

**Given** The application starts
**When** I launch the application
**Then** A log file is created in the logs/ directory

## Technical notes

- Le logger doit écrire dans logs/ à la racine du projet Electron
- Format: timestamp + level + message
- Rotation: garder les 5 derniers fichiers de 5MB
- Errors non-handled doivent être catchées et logged avec stack trace
- UI doit montrer un message user-friendly en cas d'erreur

## Files to modify

- sunshine-aio/src/main.js (handlers globaux)
- sunshine-aio/src/logger.js (nouveau)
- sunshine-aio/src/preload.js (expose logger.error à renderer)
- sunshine-aio/src/renderer.js (catch errors UI)
- sunshine-aio/src/logger.test.js (nouveau)
- sunshine-aio/package.json (deps: winston ou utiliser console)