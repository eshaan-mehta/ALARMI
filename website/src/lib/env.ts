/**
 * Typed access to Vite env vars. Only VITE_-prefixed vars reach the client.
 * Defaults to same-origin "/api" so the MSW mock works with no .env in dev.
 */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
  /** When true, start the in-browser MSW mock backend. */
  useMocks: import.meta.env.VITE_USE_MOCKS !== 'false' && import.meta.env.DEV,
} as const;
