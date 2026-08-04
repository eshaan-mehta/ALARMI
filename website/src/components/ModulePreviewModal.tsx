import { Button, Center, Group, Loader, Modal, Stack, Text } from '@mantine/core';
import { useObjectUrl } from '../data/objects/hooks';
import type { Module } from '../data/designs/types';
import { formatDimensions } from '../lib/units';
import { GlbViewer } from './GlbViewer';

interface Props {
  module: Module;
  opened: boolean;
  onClose: () => void;
}

const VIEWER_HEIGHT = '60vh';

/** Renders the module's GLB in an interactive 3D scene. */
export function ModulePreviewModal({ module, opened, onClose }: Props) {
  // The signed URL is minted on demand: nothing is requested until the modal is
  // actually open, matching how modules themselves are loaded lazily.
  const urlQuery = useObjectUrl(module.moduleId, opened);
  const label = module.type ?? 'Module';
  const dims = formatDimensions(module.dimensions, module.unitScale);

  return (
    <Modal opened={opened} onClose={onClose} title={label} size="xl" centered>
      <Stack gap="sm">
        {urlQuery.isError ? (
          <Center h={VIEWER_HEIGHT}>
            <Stack align="center" gap="xs">
              <Text size="sm" c="dimmed" ta="center">
                Couldn&apos;t load the 3D model.
              </Text>
              <Button
                variant="default"
                size="xs"
                onClick={() => urlQuery.refetch()}
                loading={urlQuery.isFetching}
              >
                Try again
              </Button>
            </Stack>
          </Center>
        ) : urlQuery.data ? (
          <GlbViewer url={urlQuery.data} alt={label} height={VIEWER_HEIGHT} />
        ) : (
          <Center h={VIEWER_HEIGHT}>
            <Loader size="sm" />
          </Center>
        )}

        <Group gap="md" justify="center">
          {dims && (
            <Text size="xs" c="dimmed">
              {dims}
            </Text>
          )}
          {module.roomId && (
            <Text size="xs" c="dimmed">
              {module.roomId}
            </Text>
          )}
        </Group>
      </Stack>
    </Modal>
  );
}
