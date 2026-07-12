import { Badge, Loader } from '@mantine/core';
import { IconAlertCircle, IconCircleCheck } from '@tabler/icons-react';
import type { ProcessingStatus } from '../data/designs/types';

const config: Record<
  ProcessingStatus,
  { label: string; color: string }
> = {
  PROCESSING: { label: 'Processing', color: 'yellow' },
  COMPLETE: { label: 'Complete', color: 'teal' },
  ERROR: { label: 'Errored', color: 'red' },
};

export function StatusBadge({ status }: { status: ProcessingStatus }) {
  const { label, color } = config[status];

  const icon =
    status === 'COMPLETE' ? (
      <IconCircleCheck size={14} />
    ) : status === 'ERROR' ? (
      <IconAlertCircle size={14} />
    ) : (
      <Loader size={12} color={color} />
    );

  return (
    <Badge color={color} variant="light" leftSection={icon} radius="sm">
      {label}
    </Badge>
  );
}
