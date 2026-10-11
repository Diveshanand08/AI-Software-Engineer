/**
 * Centralized frontend environment and API configuration.
 */

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const GOOGLE_CLIENT_ID =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  '656198371597-7321ird6jt2fn2kdjk6r6itjr21sc4t8.apps.googleusercontent.com'

export const MODE_TITLES = {
  chat: 'Chat',
  explain: 'Explain',
  bugs: 'Find Bugs',
  agent: 'Auto-Coder Agent',
  tests: 'Generate Unit Tests',
}
