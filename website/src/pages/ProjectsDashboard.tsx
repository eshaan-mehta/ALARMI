import {
  Alert,
  Button,
  Center,
  Container,
  Group,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { IconAlertTriangle, IconFolderPlus, IconPlus } from '@tabler/icons-react';
import { ProjectCard } from '../components/ProjectCard';
import { CreateProjectModal } from '../components/CreateProjectModal';
import { useProjects } from '../data/projects/hooks';

export function ProjectsDashboard() {
  const { data: projects, isLoading, isError, refetch } = useProjects();
  const [modalOpened, modal] = useDisclosure(false);

  return (
    <Container size="lg" py="xl">
      <Group justify="space-between" mb="xl">
        <div>
          <Title order={2}>Projects</Title>
          <Text c="dimmed" size="sm">
            Organize your modular designs by project.
          </Text>
        </div>
        {projects && projects.length > 0 && (
          <Button leftSection={<IconPlus size={18} />} onClick={modal.open}>
            New project
          </Button>
        )}
      </Group>

      {isLoading && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} height={140} radius="md" />
          ))}
        </SimpleGrid>
      )}

      {isError && (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={18} />}
          title="Couldn't load projects"
        >
          <Group justify="space-between">
            <Text size="sm">Something went wrong while fetching your projects.</Text>
            <Button size="xs" variant="white" color="red" onClick={() => refetch()}>
              Retry
            </Button>
          </Group>
        </Alert>
      )}

      {projects && projects.length === 0 && (
        <Center mih="50vh">
          <Stack align="center" gap="sm" maw={380} ta="center">
            <ThemeIcon size={64} radius="xl" variant="light">
              <IconFolderPlus size={32} />
            </ThemeIcon>
            <Title order={3}>No projects yet</Title>
            <Text c="dimmed" size="sm">
              Create your first project to start uploading modular design files.
            </Text>
            <Button
              size="md"
              leftSection={<IconPlus size={18} />}
              onClick={modal.open}
              mt="xs"
            >
              Create project
            </Button>
          </Stack>
        </Center>
      )}

      {projects && projects.length > 0 && (
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {projects.map((p) => (
            <ProjectCard key={p.projectId} project={p} />
          ))}
        </SimpleGrid>
      )}

      <CreateProjectModal opened={modalOpened} onClose={modal.close} />
    </Container>
  );
}
