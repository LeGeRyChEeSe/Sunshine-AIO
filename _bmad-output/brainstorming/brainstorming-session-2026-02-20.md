---
stepsCompleted: [1]
inputDocuments: []
session_topic: 'Créer un installateur complet Sunshine-AIO avec UI dédiée et intégration sunshine-aio-library'
session_goals: 'Développer un installateur clé en main avec UI unique (système solaire 3D procédural), corriger les bugs existants, intégrer le catalogue communautaire'
selected_approach: ''
techniques_used: []
ideas_generated: []
context_file: ''
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

## Prochaines Étapes Suggérées

1. Créer la spec technique détaillée (SPEC.md)
2. Prototyper l'intro "big bang" en Three.js
3. Mettre en place la structure Electron + Python IPC
4. Développer le générateur procédural de planètes
5. Intégrer le catalogue sunshine-aio-library

---

## Questions en cours
