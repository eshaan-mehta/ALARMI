import { ActionIcon, Card, Group, Menu, Stack, Text, ThemeIcon } from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconDots, IconFolder, IconPencil } from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';
import { formatDate } from '../lib/format';
import type { Project } from '../data/projects/types';
import { RenameProjectModal } from './RenameProjectModal';
import classes from './Card.module.css';

export function ProjectCard({ project }: { project: Project }) {
  const navigate = useNavigate();
  const [renameOpened, renameModal] = useDisclosure(false);
  const count = project.designCount;

  const open = () => navigate(`/projects/${project.projectId}`);

  return (
    <>
      <Card
        withBorder
        padding="lg"
        radius="md"
        className={classes.hoverable}
        onClick={open}
        style={{ cursor: 'pointer' }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter') open();
        }}
      >
        <Group justify="space-between" align="flex-start" wrap="nowrap">
          <ThemeIcon size={44} radius="md" variant="light">
            <IconFolder size={24} />
          </ThemeIcon>
          <Menu position="bottom-end" withinPortal>
            <Menu.Target>
              <ActionIcon
                variant="subtle"
                color="gray"
                aria-label="Project actions"
                onClick={(e) => e.stopPropagation()}
              >
                <IconDots size={18} />
              </ActionIcon>
            </Menu.Target>
            <Menu.Dropdown onClick={(e) => e.stopPropagation()}>
              <Menu.Item
                leftSection={<IconPencil size={16} />}
                onClick={renameModal.open}
              >
                Rename
              </Menu.Item>
            </Menu.Dropdown>
          </Menu>
        </Group>

        <Stack gap={2} mt="md">
          <Text fw={600} size="lg" lineClamp={1}>
            {project.name}
          </Text>
          <Text size="sm" c="dimmed" lineClamp={1}>
            {project.location}
          </Text>
          <Text size="sm" c="dimmed">
            {count} {count === 1 ? 'design' : 'designs'} · Created{' '}
            {formatDate(project.createdTime)}
          </Text>
        </Stack>
      </Card>

      <RenameProjectModal
        project={project}
        opened={renameOpened}
        onClose={renameModal.close}
      />
    </>
  );
}
