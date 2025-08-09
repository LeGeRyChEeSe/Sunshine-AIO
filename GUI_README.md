# 🌞 Sunshine-AIO GUI Interface

Une interface graphique moderne et user-friendly pour Sunshine-AIO, développée avec CustomTkinter.

## 🚀 Fonctionnalités

### Interface Moderne
- **Design dark/light theme** adaptatif selon le système
- **Navigation intuitive** avec sidebar et pages dédiées
- **Indicateurs de statut** en temps réel
- **Barres de progression** pour les opérations longues

### Pages Principales

#### 🏠 Main Menu
- **Installation complète** de tous les composants
- **Installations individuelles** : Sunshine, VDD, SVM, Playnite, Playnite Watcher
- **Accès rapide** aux autres sections

#### ⚙️ Extra Tools
- **Téléchargement sans installation** de tous les composants
- **Configuration Sunshine** avancée
- **Installation Windows Display Manager**
- **Accès direct** aux applications installées

#### 📥 Downloads
- **Téléchargements sélectifs** sans installation
- **Organisation par catégories** : Core, Outils, Game Management
- **Accès au dossier tools** pour gestion manuelle

#### 🗑️ Uninstall
- **Rapport d'installation** détaillé
- **Désinstallation sélective** de composants
- **Désinstallation complète** avec confirmation
- **Scan automatique** des composants installés

## 📋 Prérequis

```bash
# Dépendances requises
pip install customtkinter>=5.2.0
pip install -r requirements.txt
```

## 🖥️ Lancement

### Méthode 1 : Interface graphique
```bash
cd src
python gui_main.py
```

### Méthode 2 : Interface CLI (existante)
```bash
cd src
python main.py
```

## 🏗️ Architecture

```
src/
├── gui_main.py              # Point d'entrée GUI
├── gui/                     # Module interface graphique
│   ├── main_window.py       # Fenêtre principale
│   ├── adapters/           # Adaptateurs logique métier
│   │   └── menu_adapter.py # Interface avec MenuHandler
│   ├── components/         # Composants réutilisables
│   │   ├── status_bar.py   # Barre de statut
│   │   └── progress_dialog.py # Dialogues de progression
│   └── pages/              # Pages de l'interface
│       ├── base_page.py    # Classe de base
│       ├── main_page.py    # Page principale
│       ├── extra_page.py   # Page outils avancés
│       ├── download_page.py # Page téléchargements
│       └── uninstall_page.py # Page désinstallation
└── misc/                   # Logique métier (inchangée)
    ├── MenuHandler.py      # Contrôleur principal
    ├── Config.py           # Configuration
    └── ...                 # Autres modules existants
```

## 🔧 Avantages de l'Architecture

### Séparation des Préoccupations
- **Interface graphique** séparée de la logique métier
- **Adaptateurs** pour interfacer GUI et CLI
- **Réutilisation complète** du code existant

### Modulaire et Extensible
- **Pages indépendantes** faciles à maintenir
- **Composants réutilisables** (status bar, progress dialogs)
- **Thème unifié** avec CustomTkinter

### Backward Compatibility
- **Interface CLI préservée** intégralement
- **Logique métier inchangée** (Config, SystemRequests, etc.)
- **Possibilité de co-existence** des deux interfaces

## 🎨 Fonctionnalités Interface

### Indicateurs Visuels
- ✅ **Statut admin** - Indique les privilèges administrateur
- 🔄 **Progression en temps réel** - Barres de progression pour les opérations
- 🎯 **Feedback visuel** - Messages de succès/erreur/warning
- 📊 **État des composants** - Scan automatique des installations

### Interactions Utilisateur
- **Confirmations** pour les opérations critiques
- **Messages temporaires** informatifs
- **Navigation intuitive** entre les sections
- **Raccourcis rapides** vers les fonctions principales

### Gestion d'Erreurs
- **Dialogues d'erreur** explicites
- **Fallback gracieux** en cas de problème
- **Messages d'aide** contextuels
- **Logs détaillés** conservés

## 🚦 Utilisation

1. **Lancez l'interface** : `python gui_main.py`
2. **Sélectionnez votre action** dans la sidebar
3. **Suivez les indications** de la barre de statut
4. **Surveillez la progression** des opérations
5. **Consultez les rapports** en cas de besoin

## 🔧 Développement

### Ajout de nouvelles fonctionnalités
1. **Étendre MenuAdapter** pour exposer la nouvelle logique
2. **Créer/modifier les pages** concernées
3. **Ajouter les boutons/actions** nécessaires
4. **Tester l'intégration** avec la logique existante

### Personnalisation de l'interface
- **Thèmes** : Modifiez les couleurs dans `main_window.py`
- **Layout** : Ajustez les grids et frames dans chaque page
- **Composants** : Créez de nouveaux composants dans `/components`

## 🐛 Dépannage

### Problèmes courants
- **CustomTkinter manquant** : `pip install customtkinter`
- **Erreurs d'import** : Vérifiez les paths Python
- **Privilèges admin** : Lancez en tant qu'administrateur
- **Composants non détectés** : Utilisez le bouton "Refresh"

### Support
- **Issues GitHub** : Signalez les bugs et demandes
- **Interface CLI** : Fallback disponible avec `python main.py`
- **Logs** : Consultez les fichiers de log pour le diagnostic

## 📈 Roadmap

- [ ] **Notifications système** pour les opérations terminées
- [ ] **Thèmes personnalisés** additionnels
- [ ] **Raccourcis clavier** pour les actions courantes
- [ ] **Configuration sauvegardée** des préférences utilisateur
- [ ] **Mode expert** avec options avancées

---

**Développé avec ❤️ pour la communauté Sunshine-AIO**