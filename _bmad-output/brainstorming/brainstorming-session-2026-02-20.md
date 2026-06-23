---
stepsCompleted: [1, 4]
inputDocuments: []
session_topic: 'Créer un installateur complet Sunshine-AIO avec UI dédiée et intégration sunshine-aio-library'
session_goals: 'Développer un installateur clé en main avec UI unique (système solaire 3D procédural), corriger les bugs existants, intégrer le catalogue communautaire'
selected_approach: 'Organisation et priorisation'
techniques_used: ['Session Setup', 'UX Questions', 'Prioritization']
ideas_generated: ['30+ ideas']
context_file: ''
session_active: false
workflow_completed: true
---

# Brainstorming Session Results

**Facilitator:** Kilian
**Date:** 2026-02-20

## Session Overview

**Topic:** Créer un installateur complet Sunshine-AIO avec UI dédiée et intégration sunshine-aio-library
**Goals:** Développer un installateur clé en main avec UI unique (système solaire 3D procédural), corriger les bugs existants, intégrer le catalogue communautaire

### Idées Actuelles

#### Concept Principal: Système Solaire 3D Procédural

**Vision:** Interface sous forme de carte spatiale 3D/animée avec:
- ☀️ **Soleil** au centre - outil core Sunshine-AIO
- 🪐 **Planètes** disposées horizontalement (gauche à droite) - catégories d'apps
- 🔄 **Scroll horizontal唯一** pour naviguer entre les planètes
- 🎯 **Focus sur planète** au clic - transition animée

**Représentation des apps (selon type de planète):**
- **Planètes telluriques (rocheuses):** Apps représentées par des "pays" sur le globe 3D
- **Planètes gazeuses:** Apps représentées par des lunes en orbite autour de la planète

**Génération procédurale:** Chaque planète + type + lunes générée de manière unique et aléatoire

---

### Architecture Détaillée du Système

**Hiérarchie géographique (catégorisation):**
- ☀️ **Soleil** = Installation initiale Sunshine/Apollo (core)
- 🪐 **Planète** = Catégorie principale
- 🌍 **Continent** = 1re sous-catégorie (séparé par océans)
- 🏝️ **Pays** = 2e sous-catégorie (frontières non-linéaires)
- 🏘️ **Ville** = 3e sous-catégorie

**Fallback:**
- Si app = 1 catégorie seulement → affichée comme continent
- Si app = 2 catégories → continent + pays
- Si app = 3 catégories → continent + pays + ville

**États visuels:**
- ✅ Installé = couleur verte/bleue
- ❌ Non-installé = gris
- ⚔️ En cours d'installation = animation d'envahisseurs (chevaliers, armées, chars)
- 💥 Désinstallation = animation de dévastation (bombe nucléaire, incendie, déforestation)

**Thèmes d'invasion:** Aléatoire parmi plusieurs presets (chevaliers, armées, chars, robots, extraterrestres, pirates...)

**Nommage:**
- Planète/Continent = nom de la catégorie
- Si 1 seule app dans la catégorie = nom de l'app directement
- Noms procéduraux style "Kurzgesagt" -干净, factuel

---

### Flux d'Installation (Big Bang)

**Intro:**
1. Écran noir total
2. Texte animation: "Au début il n'y avait rien..." (style narratif impactant)
3. "Big bang" - explosion visuelle
4. Le soleil apparaît + se forme pendant installation Sunshine/Apollo
5. Les planètes se créent au fur et à mesure que les outils sont installés
6. Une fois core installé → planètes grisées (outils communautaires) apparaissent

**Post-install:**
- Vue d'ensemble du système solaire avec toutes les planètes (installées + communautaires)
- Navigation horizontale entre les planètes

---

### Style Visuel (Référence Kurzgesagt)

**Características:**
- Style dessin animé procédural
- Gros traits épais (thick outlines)
- Animations fluides et expressives
- Esthétique distinctives, pas " générique AI"
- Biomes aléatoires par planète (désert, forêt, océan, glace, volcanique...)
- Un biome par planète, pas par sous-catégorie

---

### Animations d'Invasion (Installation)

**Concept:** On voit uniquement l'envahisseur arriver sur terre vide
**Thèmes possibles (aléatoire):**
- Chevaliers médiévaux
- Armée romaine
- Soldats modernes / chars
- Robots / Mechas
- Extraterrestres
- Pirates
- Vikings
- samouraïs

**Animation:** L'envahisseur "prend possession" de la zone (continent/pays/ville)

---

### Animations de Désinstallation (Dévastation)

**Par type de région:**
- 🪐 **Planète entière** = explosion planétaire + réaggrégation en planète grisée
- 🌍 **Continent** = bombe nucléaire (champignon + radiation)
- 🏝️ **Pays** = déforestation massive (bulldozers, arbres qui tombent)
- 🏘️ **Ville** = incendie (feu qui se répand)

---

---

### Stack Technique

**Frontend:** Electron + Three.js
**Backend:** Question ouverte - Python (existant) vs Rust (performance) vs autre
- Option A: Electron + Python (backend via IPC)
- Option B: Electron + Rust (backend)
- Option C: Tout en JavaScript/TypeScript

**Services:**
- Background service léger pour notifications d'updates

---

### Flux d'Installation (Big Bang) - DÉTAILLÉ

**État initial:**
- Écran noir total
- Point brillant blanc au centre (singularité)
- Texte sobre, minimaliste

**Interaction utilisateur:**
- Cliquer n'importe où → lance le "big bang" = installation automatique

**Apps installées lors du big bang:**
1. Sunshine (ou Apollo selon choix utilisateur)
2. Virtual Display Driver (VDD)
3. Sunshine-Virtual-Monitor
4. Playnite
5. Playnite Watcher

**Création de l'univers:**
- Durée = temps d'installation des outils de base
- Le soleil se forme/éclate progressivement
- Les planètes apparaissent au fur et à mesure des installations
- Animation synchrone avec la progression d'installation

**État final:**
- Système solaire complet avec planètes installées (couleurs)
- Planètes grisées pour apps communautaires disponibles

---

### Intro Phrase Selection

**Selected:** "Every great stream starts in the dark. Let's bring the light."

---

## Décisions Finales

- ✅ **Backend:** Python (via IPC avec Electron)
- ✅ **Frontend:** Electron + Three.js
- ✅ **Concept:** Système solaire 3D procédural avec métaphore géographique
- ✅ **Style:** Dessin animé procédural style Kurzgesacht
- ✅ **Catalogue:** sunshine-aio-library

---

## Suite du Brainstorming

*(Reprise du brainstorming - pas de code pour l'instant)*

### Questions de perforation supplémentaires

**Sur l'expérience utilisateur :**

1. **Premiers pas utilisateur** - Comment l'utilisateur découvre-t-il qu'il peut installer des apps communautaires ? Il y a un indicateur visuel sur les planètes grisées ?

2. **Recherche d'apps** - Tu prévois un moyen de rechercher une app spécifique ou on passe que par la navigation planètes ?

3. **Détails d'une app** - Quand on clique sur une "ville" (app), on voit quoi ? Screenshot ? Description ? Version ? Bouton install ?

4. **Updates** - Comment l'user voit qu'une app a une update dispo ? Icône ? Badge ? Notification ?

**Sur le système solaire :**

5. **Nombre de planètes** - Tu prévois combien de catégories max ? 5 ? 10 ? Plus ?

6. **Ordre des planètes** - C'est trié comment ? Alphabétique ? Par usage ? Aléatoire ?

7. **Planètes vides** - Si une catégorie n'a pas encore d'apps communautaires, la planète existe quand même ou elle apparaît quand la première app est ajoutée ?

**Technique :**

8. **Sauvegarde de l'état** - Si l'utilisateur ferme l'app et rouvre, le système solaire est régénéré ou restauré à l'identique ?

9. **Mode offline** - L'app fonctionne sans internet ? Pour installer des updates, le catalogue doit être sync comment ?

10. **Compatibilité** - C'est Windows only pour le début ou tu prévois direct le cross-platform ?

---

## Questions en cours

*(Réponses du 21 février 2026)*

### Expérience Utilisateur

**1. Découverte des apps communautaires**
- ✅ Les planètes grisées et **clignotantes** indiquent que des apps sont disponibles
- ✅ Elles seront **luminescentes** (effet glow)
- ✅ **Liste classique parallèle** intégrée à part pour ceux qui ne veulent pas de la UI custom

**2. Détails d'une app (carte de visite)**
- ✅ Page **translucide** style "carte de visite"
- ✅ **Single page scrollable** (tout sur une page)
- ✅ Affiche: **screenshots** (si disponibles), **description**, **version**
- ✅ Bouton **installer** visible

**3. Updates**
- ✅ **Notification système** (bureau) quand une update est dispo
- ✅ **Indicateur dans l'app:** Planète qui **pulse** avec un halo lumineux (donc la planète de la catégorie qui contient une app avec update)

### Système Solaire

**5. Nombre de planètes**
- ✅ Défini par **sunshine-aio-library**
- ✅ Maximum **10-20** catégories (pas des centaines)
- ✅ Au début: pas beaucoup de catégories

**6. Ordre des planètes**
- ✅ **Pas important** - tri aléatoire

**7. Planètes vides**
- ✅ Le monde n'est généré **procéduralement qu'une seule fois** au premier démarrage

### Technique

**8. Sauvegarde de l'état**
- ✅ Le monde est **généré une seule fois** au premier lancement
- ✅ État sauvegardé et restauré à l'identique à chaque ouverture
- ✅ Option dans les paramètres pour **régénérer le monde** (sans modifier les apps affichées)

**9. Mode offline**
- ✅ L'app fonctionne **avec et sans internet**
- ✅ Au démarrage: récupération de la liste des apps dispo (ou à la demande via refresh)
- ✅ Téléchargement des apps depuis GitHub ou autre source

**10. Compatibilité**
- ✅ **Windows only** pour le moment

---

### Priorisation des Idées

**Top 3 Priorités:**

1. **Système solaire 3D procédural** - Cœur de l'identité visuelle unique
2. **Page translucide "carte de visite"** - UX critique pour installer des apps
3. **Notifications + indicateur pulse** - Maintient l'utilisateur informé des updates

**Quick Wins:**
- Liste classique parallèle
- Mode offline
- Sauvegarde de l'état

**Concepts Breakthrough:**
- Animations d'invasion/dévastation
- Intro "Big Bang"
- Régénération du monde

---

### Plans d'Action

#### Priorité 1: Système Solaire 3D Procédural

**Pourquoi c'est important:** C'est l'élément différenciant principal du projet - l'identité visuelle unique qui rend l'installateur mémorable.

**Étapes next:**
1. Configurer l'environnement Electron + Three.js
2. Créer la scène 3D de base avec le soleil
3. Implémenter la génération procédurale des planètes
4. Ajouter le scroll horizontal entre planètes
5. Intégrer les états visuels (installé/non-installé/gris)

**Ressources nécessaires:**
- Compétences Three.js / WebGL
- Temps estimé: Phase 1 du développement

**Indicateurs de succès:**
- Le système solaire s'affiche correctement
- Navigation fluide entre les planètes
- États visuels fonctionnels

---

#### Priorité 2: Page Translucide "Carte de Visite"

**Pourquoi c'est important:** UX critique - c'est comment l'utilisateur découvre et installe les apps communautaires.

**Étapes next:**
1. Designer la structure de la page (overlay translucide)
2. Intégrer l'affichage des screenshots
3. Ajouter les infos: description, version, bouton installer
4. Rendre la page scrollable
5. Connecter au système d'installation

**Ressources nécessaires:**
- Compétences UI/UX Electron
- Accès aux métadonnées des apps (screenshots, descriptions)

**Indicateurs de succès:**
- Page s'affiche au clic sur une ville/planète
- Tous les infos visibles et correctement formatés
- Bouton installer fonctionnel

---

#### Priorité 3: Notifications + Indicateur Pulse

**Pourquoi c'est important:** Maintient l'utilisateur informé des updates sans qu'il ait à chercher.

**Étapes next:**
1. Implémenter le système de notifications système (Electron Notification API)
2. Créer l'animation "pulse avec halo" pour les planètes avec update
3. Connecter au système de vérification des updates
4. Gérer le cas où l'app est fermée (background service)

**Ressources nécessaires:**
- API de notification Electron
- Logique de vérification des versions

**Indicateurs de succès:**
- Notification reçue quand une update est dispo
- Planète pulse visuellement quand une app a une update

---

## Résumé de Session et Prochaines Étapes

### Réalisations Clés

- **Concept unique défini:** Système solaire 3D procédural comme interface principale
- **UX complétée:** Découverte des apps communautaires, page details, updates
- **Stack technique validée:** Electron + Three.js + Python (IPC)
- **Priorités actionnables:** 3 niveaux de priorité clairement définis
- **30+ idées** générées et organisées en 5 thèmes

### Prochaines Étapes

1. **Commencer par la Priorité 1** - Configurer Electron + Three.js
2. **Documenter le projet** - Créer le PRD et l'architecture
3. **Planifier le développement** - Découper en stories exploitables

### Session Insights

- L'idée du système solaire est très originale et différenciante
- Les animations d'invasion/dévastation ajoutent du caractère
- La liste classique parallèle est un bon compromis accessibilité
- Le mode offline est un gros plus pour l'expérience utilisateur

---

**Session complétée le 21 février 2026**