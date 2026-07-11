import axios from 'axios';
import { env } from '../lib/env';

/**
 * Single axios instance. Base URL comes from env (defaults to same-origin /api,
 * which the MSW mock intercepts in dev). Swap VITE_API_BASE_URL for the real
 * backend — no other code changes needed.
 */
export const http = axios.create({
  baseURL: env.apiBaseUrl,
});
