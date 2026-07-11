import { Badge, Loader } from '@mantine/core';
import { IconCircleCheck, IconClock } from '@tabler/icons-react';
import type { ProcessingStatus } from '../data/designs/types';

const config: Record<
  ProcessingStatus,
  { label: string; color: string }
> = {
  NONE: { label: 'Queued', color: 'gray' },
  IN_PROGRESS: { label: 'Processing', color: 'yellow' },
  COMPLETE: { label: 'Ready', color: 'teal' },
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const { label, color } = config[status];

  const icon =
    status === 'COMPLETE' ? (
      <IconCircleCheck size={14} />
    ) : status === 'IN_PROGRESS' ? (
      <Loader size={12} color={color} />
    ) : (
      <IconClock size={14} />
    );

  return (
    <Badge color={color} variant="light" leftSection={icon} radius="sm">
      {label}
    </Badge>
  );
}
