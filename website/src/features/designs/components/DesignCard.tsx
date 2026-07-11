import {
  ActionIcon,
  Card,
  Divider,
  Group,
  Menu,
  Stack,
  Text,
  ThemeIcon,
} from '@mantine/core';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import { IconDots, IconFile3d, IconTrash } from '@tabler/icons-react';
import { formatBytes, formatDate } from '../../../lib/format';
import { useDeleteDesign } from '../hooks';
import type { Design } from '../types';
import { StatusBadge } from './StatusBadge';

interface Props {
  design: Design;
  projectName: string;
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <Group justify="space-between" gap="xs">
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text size="xs" fw={500} ta="right">
        {value}
      </Text>
    </Group>
  );
}

export function DesignCard({ design, projectName }: Props) {
  const del = useDeleteDesign(projectName);

  const confirmDelete = () =>
    modals.openConfirmModal({
      title: 'Delete design',
      centered: true,
      children: (
        <Text size="sm">
          Delete “{design.name}”? This removes the design file, its generated
          outputs, and metadata. This can&apos;t be undone.
        </Text>
      ),
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () =>
        del.mutate(design.designId, {
          onSuccess: () =>
            notifications.show({
              color: 'gray',
              title: 'Design deleted',
              message: `“${design.name}” was removed.`,
            }),
        }),
    });

  const isReady = design.status === 'COMPLETE';

  return (
    <Card withBorder padding="lg" radius="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Group gap="sm" wrap="nowrap">
          <ThemeIcon size={40} radius="md" variant="light">
            <IconFile3d size={22} />
          </ThemeIcon>
          <div>
            <Text fw={600} lineClamp={1}>
              {design.name}
            </Text>
            <Text size="xs" c="dimmed" lineClamp={1}>
              {design.fileName}
            </Text>
          </div>
        </Group>

        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray" aria-label="Design actions">
              <IconDots size={18} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              color="red"
              leftSection={<IconTrash size={16} />}
              onClick={confirmDelete}
            >
              Delete
            </Menu.Item>
          </Menu.Dropdown>
        </Menu>
      </Group>

      <Group justify="space-between" mt="md">
        <StatusBadge status={design.status} />
        <Text size="xs" c="dimmed">
          {formatBytes(design.fileSize)} · {formatDate(design.uploadTime)}
        </Text>
      </Group>

      {isReady && (
        <>
          <Divider my="sm" />
          <Stack gap={6}>
            {design.moduleType && (
              <MetaRow label="Type" value={design.moduleType} />
            )}
            {design.dimensions && (
              <MetaRow
                label="Dimensions"
                value={`${design.dimensions.x} × ${design.dimensions.y} × ${design.dimensions.z} m`}
              />
            )}
            {design.anchorCount != null && (
              <MetaRow label="Anchor points" value={String(design.anchorCount)} />
            )}
            {design.roomId && <MetaRow label="Room" value={design.roomId} />}
          </Stack>
        </>
      )}
    </Card>
  );
}
