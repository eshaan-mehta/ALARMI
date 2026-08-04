import { http } from '../http';

/** Shape of GET /api/objects/get_url/{moduleId} — see backend ObjectUrlOut. */
interface ObjectUrlResponse {
  url: string;
}

/**
 * GET /api/objects/get_url/{moduleId} — a presigned URL to the module's GLB in
 * blob storage. The client never sees a storage key or credential, and the URL
 * is short-lived (the backend signs it for an hour), so it's fetched on demand
 * rather than stored alongside the module's metadata.
 */
export async function getObjectUrl(moduleId: string): Promise<string> {
  const { data } = await http.get<ObjectUrlResponse>(
    `/objects/get_url/${moduleId}`,
  );
  // Same guard as the list endpoints: a body without a url means the request
  // didn't reach the backend, so fail here instead of handing the viewer
  // `undefined` and getting an opaque load error.
  if (typeof data?.url !== 'string') {
    throw new Error('Expected a url from /objects/get_url/{moduleId}');
  }
  return data.url;
}
