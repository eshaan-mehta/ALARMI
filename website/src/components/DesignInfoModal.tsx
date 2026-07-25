import { Group, Modal, Stack, Text } from '@mantine/core';
import { formatBytes, formatDate } from '../lib/format';
import type { Design } from '../data/designs/types';
import { StatusBadge } from './StatusBadge';

interface Props {
  design: Design;
  opened: boolean;
  onClose: () => void;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <Group justify="space-between" gap="xl" wrap="nowrap" align="flex-start">
      <Text size="sm" c="dimmed" style={{ flexShrink: 0 }}>
        {label}
      </Text>
      <Text size="sm" fw={500} ta="right" style={{ wordBreak: 'break-word' }}>
        {value}
      </Text>
    </Group>
  );
}

/**
 * Design-level metadata only. The extracted modules are shown in the design
 * row's expandable panel, so they're intentionally not duplicated here.
 */
export function DesignInfoModal({ design, opened, onClose }: Props) {
  return (
    <Modal opened={opened} onClose={onClose} title="Design info" centered>
      <Stack gap="sm">
        <InfoRow label="Name" value={design.name} />
        <InfoRow label="File" value={design.fileName} />
        <InfoRow label="Size" value={formatBytes(design.fileSize)} />
        <Group justify="space-between" gap="xl" wrap="nowrap">
          <Text size="sm" c="dimmed">
            Status
          </Text>
          <StatusBadge status={design.status} />
        </Group>
        <InfoRow label="Uploaded" value={formatDate(design.uploadTime)} />
        <InfoRow label="Modules" value={String(design.moduleCount)} />
        <InfoRow label="Design ID" value={design.designId} />
      </Stack>
    </Modal>
  );
}
