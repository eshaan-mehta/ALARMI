import { useState } from 'react';
import {
  ActionIcon,
  Card,
  Collapse,
  Divider,
  Group,
  Menu,
  Paper,
  SimpleGrid,
  Text,
  ThemeIcon,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconChevronRight,
  IconCube,
  IconDots,
  IconFile3d,
  IconInfoCircle,
  IconPencil,
  IconTrash,
} from '@tabler/icons-react';
import { useDeleteDesign } from '../data/designs/hooks';
import type { Design, Module } from '../data/designs/types';
import { StatusBadge } from './StatusBadge';
import { DesignInfoModal } from './DesignInfoModal';
import { EditModuleModal } from './EditModuleModal';
import { RenameDesignModal } from './RenameDesignModal';
import classes from './Card.module.css';

interface Props {
  design: Design;
  projectId: string;
}

function dims(m: Module): string | null {
  if (!m.dimensions) return null;
  const { x, y, z } = m.dimensions;
  return `${x} × ${y} × ${z} m`;
}

/** One labelled metadata line inside a module tile. */
function MetaLine({ label, value }: { label: string; value: string }) {
  return (
    <Group justify="space-between" gap="md" wrap="nowrap" align="flex-start">
      <Text size="xs" c="dimmed" style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Text size="xs" fw={500} ta="right" style={{ wordBreak: 'break-word' }}>
        {value}
      </Text>
    </Group>
  );
}

/** A single module rendered with all of its metadata, plus per-module actions. */
function ModuleTile({ module, onEdit }: { module: Module; onEdit: () => void }) {
  const d = dims(module);
  return (
    <Paper withBorder radius="sm" p="sm">
      <Group justify="space-between" gap="xs" wrap="nowrap" mb={6}>
        <Text size="sm" fw={600} lineClamp={1}>
          {module.type ?? 'Module'}
        </Text>
        <Group gap={2} wrap="nowrap">
          <Tooltip label="Edit metadata" withArrow>
            <ActionIcon
              variant="subtle"
              color="gray"
              aria-label={`Edit ${module.type ?? 'module'} metadata`}
              onClick={onEdit}
            >
              <IconPencil size={16} />
            </ActionIcon>
          </Tooltip>
          {/* Placeholder for the upcoming 3D module preview. */}
          <Tooltip label="3D preview — coming soon" withArrow>
            <ActionIcon
              variant="subtle"
              color="gray"
              aria-label="Preview module in 3D"
              data-disabled
              onClick={(e) => e.preventDefault()}
            >
              <IconCube size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>
      <Divider mb={6} />
      {d && <MetaLine label="Dimensions" value={d} />}
      {module.roomId && <MetaLine label="Room" value={module.roomId} />}
      {module.unitScale && <MetaLine label="Unit scale" value={module.unitScale} />}
      <MetaLine label="Module ID" value={module.moduleId} />
    </Paper>
  );
}

export function DesignCard({ design, projectId }: Props) {
  const del = useDeleteDesign(projectId);
  const [expanded, { toggle }] = useDisclosure(false);
  const [renameOpened, renameModal] = useDisclosure(false);
  const [infoOpened, infoModal] = useDisclosure(false);
  const [editModule, setEditModule] = useState<Module | null>(null);

  const confirmDelete = () =>
    modals.openConfirmModal({
      title: 'Delete design',
      centered: true,
      children: (
        <Text size="sm">
          Delete “{design.name}”? This removes the design file, its generated
          outputs, and all extracted modules. This can&apos;t be undone.
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

  const isProcessing = design.status === 'PROCESSING';
  const moduleCount = design.modules.length;
  // Only COMPLETE designs with extracted modules can be expanded.
  const expandable = design.status === 'COMPLETE' && moduleCount > 0;

  return (
    <>
      <Card
        withBorder
        padding="md"
        radius="md"
        className={isProcessing ? classes.processing : undefined}
      >
        <Group justify="space-between" align="center" wrap="nowrap">
          <Group
            gap="sm"
            wrap="nowrap"
            style={{ minWidth: 0, flex: 1, cursor: expandable ? 'pointer' : 'default' }}
            onClick={expandable ? toggle : undefined}
            role={expandable ? 'button' : undefined}
            tabIndex={expandable ? 0 : undefined}
            aria-expanded={expandable ? expanded : undefined}
            onKeyDown={(e) => {
              if (expandable && (e.key === 'Enter' || e.key === ' ')) {
                e.preventDefault();
                toggle();
              }
            }}
          >
            {expandable ? (
              <IconChevronRight
                size={18}
                style={{
                  flexShrink: 0,
                  transition: 'transform 150ms ease',
                  transform: expanded ? 'rotate(90deg)' : 'none',
                }}
              />
            ) : (
              <span style={{ width: 18, flexShrink: 0 }} />
            )}
            <ThemeIcon size={38} radius="md" variant="light">
              <IconFile3d size={20} />
            </ThemeIcon>
            <div style={{ minWidth: 0 }}>
              <Text fw={600} lineClamp={1}>
                {design.name}
              </Text>
              <Group gap="xs" wrap="nowrap" mt={2}>
                <StatusBadge status={design.status} />
                {moduleCount > 0 && (
                  <Text size="xs" c="dimmed">
                    · {moduleCount} {moduleCount === 1 ? 'module' : 'modules'}
                  </Text>
                )}
              </Group>
            </div>
          </Group>

          <Menu position="bottom-end" withinPortal>
            <Menu.Target>
              <ActionIcon
                variant="subtle"
                color="gray"
                aria-label="Design actions"
                onClick={(e) => e.stopPropagation()}
              >
                <IconDots size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown onClick={(e) => e.stopPropagation()}>
              <Menu.Item
                leftSection={<IconInfoCircle size={16} />}
                onClick={infoModal.open}
              >
                Info
              </Menu.Item>
              <Menu.Item
                leftSection={<IconPencil size={16} />}
                onClick={renameModal.open}
              >
                Rename
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

        {expandable && (
          <Collapse expanded={expanded}>
            <Divider my="sm" />
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
              {design.modules.map((m) => (
                <ModuleTile
                  key={m.moduleId}
                  module={m}
                  onEdit={() => setEditModule(m)}
                />
              ))}
            </SimpleGrid>
          </Collapse>
        )}
      </Card>

      <RenameDesignModal
        design={design}
        projectId={projectId}
        opened={renameOpened}
        onClose={renameModal.close}
      />

      <DesignInfoModal
        design={design}
        opened={infoOpened}
        onClose={infoModal.close}
      />

      {editModule && (
        <EditModuleModal
          module={editModule}
          projectId={projectId}
          opened={editModule !== null}
          onClose={() => setEditModule(null)}
        />
      )}
    </>
  );
}
