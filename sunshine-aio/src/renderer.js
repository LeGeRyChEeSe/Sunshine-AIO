import './styles.css';

/**
 * Sunshine AIO Renderer Process
 *
 * This file handles the UI rendering for the desktop application.
 * Current implementation: Basic HTML rendering with stylesheet.
 *
 * For Story 1.3+ (Python backend integration):
 * - Use IPC via window.electronAPI to communicate with main process
 * - IPC channels (will be defined in Story 1.3):
 *   - 'app:get-installed-apps' - Get list of installed applications
 *   - 'app:install-app' - Install an application
 *   - 'app:uninstall-app' - Uninstall an application
 *   - 'app:get-catalog' - Get application catalog
 *
 * Example IPC usage (to be implemented in Story 1.3+):
 *   const apps = await window.electronAPI.invoke('app:get-installed-apps');
 *
 * Error handling example:
 *   try {
 *     const apps = await window.electronAPI.invoke('app:get-installed-apps');
 *     console.log('Installed apps:', apps);
 *   } catch (error) {
 *     console.error('Failed to get apps:', error.message);
 *     // Show user-friendly error message
 *   }
 *
 * UI Framework: Plain JavaScript for now, consider React for complex UI later
 * State Management: Will use Zustand in Story 2.1
 */
