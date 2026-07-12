import { Divider, Group, Modal, Stack, Text } from '@mantine/core';
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

export function DesignInfoModal({ design, opened, onClose }: Props) {
  const isComplete = design.status === 'COMPLETE';

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
        <InfoRow label="Design ID" value={design.designId} />

        {isComplete && (
          <>
            <Divider label="Metadata" labelPosition="left" my={4} />
            {design.moduleType && <InfoRow label="Type" value={design.moduleType} />}
            {design.dimensions && (
              <InfoRow
                label="Dimensions"
                value={`${design.dimensions.x} × ${design.dimensions.y} × ${design.dimensions.z} m`}
              />
            )}
            {design.anchorCount != null && (
              <InfoRow label="Anchor points" value={String(design.anchorCount)} />
            )}
            {design.roomId && <InfoRow label="Room" value={design.roomId} />}
            {design.unitScale && <InfoRow label="Unit scale" value={design.unitScale} />}
          </>
        )}
      </Stack>
    </Modal>
  );
}
