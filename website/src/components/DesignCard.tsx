import {
  ActionIcon,
  Card,
  Divider,
  Group,
  Loader,
  Menu,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertCircle,
  IconDots,
  IconFile3d,
  IconInfoCircle,
  IconPencil,
  IconTrash,
} from '@tabler/icons-react';
import { useDeleteDesign } from '../data/designs/hooks';
import type { Design } from '../data/designs/types';
import { DesignInfoModal } from './DesignInfoModal';
import { EditDesignModal } from './EditDesignModal';
import classes from './Card.module.css';

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
  const [editOpened, editModal] = useDisclosure(false);
  const [infoOpened, infoModal] = useDisclosure(false);

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
  const isProcessing = design.status === 'PROCESSING';
  const hasError = design.status === 'ERROR';

  return (
    <>
      <Card
        withBorder
        padding="lg"
        radius="md"
        className={`${classes.hoverable} ${isProcessing ? classes.processing : ''}`}
      >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Group gap="sm" wrap="nowrap">
          <ThemeIcon
            size={40}
            radius="md"
            variant="light"
            color={hasError ? 'red' : undefined}
          >
            <IconFile3d size={22} />
          </ThemeIcon>
          <Text fw={600} lineClamp={1}>
            {design.name}
          </Text>
          {hasError && (
            <Tooltip label="Upload failed — open Info for details" withArrow>
              <ThemeIcon size={20} radius="xl" color="red" variant="light">
                <IconAlertCircle size={16} />
              </ThemeIcon>
            </Tooltip>
          )}
        </Group>

        <Menu position="bottom-end" withinPortal>
          <Menu.Target>
            <ActionIcon variant="subtle" color="gray" aria-label="Design actions">
              <IconDots size={18} />
            </ActionIcon>
          </Menu.Target>
          <Menu.Dropdown>
            <Menu.Item
              leftSection={<IconInfoCircle size={16} />}
              onClick={infoModal.open}
            >
              Info
            </Menu.Item>
            <Menu.Item
              leftSection={<IconPencil size={16} />}
              onClick={editModal.open}
            >
              Edit
            </Menu.Item>
            <Menu.Divider />
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

      {isProcessing && (
        <Group gap="xs" mt="md">
          <Loader size="xs" color="yellow" />
          <Text size="sm" c="dimmed">
            Processing…
          </Text>
        </Group>
      )}

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

      <EditDesignModal
        design={design}
        projectName={projectName}
        opened={editOpened}
        onClose={editModal.close}
      />

      <DesignInfoModal
        design={design}
        opened={infoOpened}
        onClose={infoModal.close}
      />
    </>
  );
}
