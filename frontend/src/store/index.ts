/**
 * Zustand state stores for NovaSight
 * 
 * Global state management using Zustand:
 * - UI state (sidebar, modals, etc.)
 * - User preferences
 * - Application-wide settings
 * - Authentication state
 */

export { useUIStore } from './uiStore'
export { useAuthStore } from './authStore'
export type { AuthState, RegisterData } from './authStore'
