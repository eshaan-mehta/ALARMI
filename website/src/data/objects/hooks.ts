import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../queryKeys';
import { getObjectUrl } from './api';

/** The backend signs GLB URLs for one hour (blob.py `_URL_TTL_HOURS`). Treating
 * one as stale well before then means a long-lived tab never hands the viewer a
 * URL that expires mid-load. */
const SIGNED_URL_STALE_MS = 45 * 60 * 1000;

/**
 * Lazily fetches the presigned URL for one module's GLB. Stays disabled until
 * `enabled` (the preview modal is open), mirroring `useDesignModules` — no
 * point minting a signed URL for every module in a design when the user only
 * ever previews one at a time.
 */
export function useObjectUrl(moduleId: string, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.moduleObjectUrl(moduleId),
    queryFn: () => getObjectUrl(moduleId),
    enabled,
    staleTime: SIGNED_URL_STALE_MS,
    gcTime: SIGNED_URL_STALE_MS,
  });
}
