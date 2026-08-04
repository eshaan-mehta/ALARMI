import { useEffect, useRef, useState } from 'react';
import { Box, Center, Loader, Stack, Text } from '@mantine/core';
import { IconCubeOff } from '@tabler/icons-react';
import type { ModelViewerElement } from '@google/model-viewer';

/**
 * `<model-viewer>` is a custom element, so React needs to be told the tag
 * exists and which attributes it accepts. Only the attributes this app actually
 * sets are declared — the element supports many more.
 *
 * Presence-style boolean attributes are typed as `''` rather than `boolean`:
 * model-viewer reads them by presence, and React serialises `false` on a custom
 * element to the string "false" (which is *present*, hence truthy). Passing an
 * empty string keeps the canonical HTML boolean-attribute shape and removes the
 * ambiguity entirely.
 */
declare module 'react' {
  // Augmenting JSX.IntrinsicElements is the only way to teach TS about a custom
  // element, and it requires a namespace — there's no module-syntax equivalent.
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement>,
        HTMLElement
      > & {
        src?: string;
        alt?: string;
        'camera-controls'?: '';
        'auto-rotate'?: '';
        'shadow-intensity'?: string;
        'environment-image'?: string;
        'touch-action'?: string;
      };
    }
  }
}

type Status = 'loading' | 'ready' | 'error';

interface Props {
  /** Presigned URL to the GLB. */
  url: string;
  /** Accessible description of what's being rendered. */
  alt: string;
  /** CSS height of the canvas. */
  height?: string;
}

/**
 * Renders a GLB in an interactive 3D scene — orbit, zoom, pan.
 *
 * This is the seam between the app and whatever draws the geometry. Everything
 * around it (the modal, the data fetch, the error copy) talks to this component
 * through `url` alone, so replacing model-viewer with a hand-built three.js /
 * react-three-fiber scene later — the thing you'd need for showing several
 * modules positioned in one scene — is a rewrite of this file and nothing else.
 *
 * model-viewer is ~150KB, so the element is registered via a dynamic import on
 * mount: it's only fetched once a user actually opens a preview, and never
 * lands in the main bundle.
 */
export function GlbViewer({ url, alt, height = '60vh' }: Props) {
  const ref = useRef<ModelViewerElement>(null);
  const [defined, setDefined] = useState(false);
  const [status, setStatus] = useState<Status>('loading');

  // Register the custom element. Runs once; the import is cached after that, so
  // reopening a preview is instant.
  useEffect(() => {
    let cancelled = false;
    import('@google/model-viewer')
      .then(() => !cancelled && setDefined(true))
      .catch(() => !cancelled && setStatus('error'));
    return () => {
      cancelled = true;
    };
  }, []);

  // model-viewer reports load success/failure with plain DOM CustomEvents, not
  // React synthetic events, so they're subscribed on the node directly. Rebound
  // when the src changes so a second model reports its own outcome.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setStatus('loading');
    const onLoad = () => setStatus('ready');
    const onError = () => setStatus('error');
    el.addEventListener('load', onLoad);
    el.addEventListener('error', onError);
    return () => {
      el.removeEventListener('load', onLoad);
      el.removeEventListener('error', onError);
    };
  }, [defined, url]);

  if (status === 'error') {
    return (
      <Center h={height}>
        <Stack align="center" gap="xs">
          <IconCubeOff size={32} stroke={1.5} color="var(--mantine-color-dimmed)" />
          <Text size="sm" c="dimmed" ta="center">
            Couldn&apos;t load the 3D model.
          </Text>
        </Stack>
      </Center>
    );
  }

  return (
    <Box pos="relative" h={height}>
      {defined && (
        <model-viewer
          ref={ref}
          src={url}
          alt={alt}
          camera-controls=""
          auto-rotate=""
          shadow-intensity="1"
          environment-image="neutral"
          // Vertical drags orbit the model rather than scrolling the modal,
          // which is what makes it feel like a 3D viewport on touch.
          touch-action="none"
          style={{ width: '100%', height: '100%', backgroundColor: 'transparent' }}
        />
      )}
      {/* Overlaid rather than swapped in, so the element stays mounted and keeps
          loading underneath the spinner. */}
      {status === 'loading' && (
        <Center pos="absolute" inset={0}>
          <Loader size="sm" />
        </Center>
      )}
    </Box>
  );
}
