import { Card, Group, Stack, Text, ThemeIcon } from '@mantine/core';
import { IconFolder, IconChevronRight } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { formatDate } from '../../../lib/format';
import type { Project } from '../types';

export function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate();
  const count = project.designCount;

  return (
    <Card
      withBorder
      padding="lg"
      radius="md"
      onClick={() => navigate(`/projects/${encodeURIComponent(project.name)}`)}
      style={{ cursor: 'pointer' }}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter')
          navigate(`/projects/${encodeURIComponent(project.name)}`);
      }}
    >
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <ThemeIcon size={44} radius="md" variant="light">
          <IconFolder size={24} />
        </ThemeIcon>
        <IconChevronRight size={18} color="var(--mantine-color-dimmed)" />
      </Group>

      <Stack gap={2} mt="md">
        <Text fw={600} size="lg" lineClamp={1}>
          {project.name}
        </Text>
        <Text size="sm" c="dimmed">
          {count} {count === 1 ? 'design' : 'designs'} · Created{' '}
          {formatDate(project.createdTime)}
        </Text>
      </Stack>
    </Card>
  );
}
