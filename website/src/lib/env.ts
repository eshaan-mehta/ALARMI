/**
 * Typed access to Vite env vars. Only VITE_-prefixed vars reach the client.
 * Defaults to same-origin "/api"; point at the backend with VITE_API_BASE_URL.
 */
export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '/api',
} as const;
