import {
  Alert,
  Anchor,
  Button,
  Center,
  Container,
  Group,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCloudUpload,
  IconUpload,
} from '@tabler/icons-react';
import { Link, useParams } from 'react-router-dom';
import { DesignCard } from '../components/DesignCard';
import { UploadModal } from '../components/UploadModal';
import { useProjectDesigns } from '../data/designs/hooks';
import { useProject } from '../data/projects/hooks';

export function ProjectDetail() {
  const { projectId = '' } = useParams();
  const { project, isLoading: projectLoading, isSuccess: projectsLoaded } =
    useProject(projectId);
  const {
    data: designs,
    isLoading,
    isError,
    refetch,
  } = useProjectDesigns(projectId);
  const [modalOpened, modal] = useDisclosure(false);

  // The projects list resolved but no project has this id.
  const notFound = projectsLoaded && !project;

  return (
    <Container size="lg" py="xl">
      <Anchor
        component={Link}
        to="/projects"
        size="sm"
        c="dimmed"
        mb="md"
        style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
      >
        <IconArrowLeft size={16} /> All projects
      </Anchor>

      {notFound ? (
        <Alert
          color="red"
          icon={<IconAlertTriangle size={18} />}
          title="Project not found"
        >
          <Text size="sm">
            This project doesn&apos;t exist or may have been removed.{' '}
            <Anchor component={Link} to="/projects">
              Back to all projects
            </Anchor>
            .
          </Text>
        </Alert>
      ) : (
        <>
          <Group justify="space-between" mb="xl" align="flex-end">
            <div>
              {projectLoading ? (
                <Skeleton height={30} width={240} mb={6} />
              ) : (
                <Title order={2}>{project?.name}</Title>
              )}
              <Text c="dimmed" size="sm">
                {project?.location ? `${project.location} · ` : ''}
                {designs ? `${designs.length} ` : ''}
                design{designs?.length === 1 ? '' : 's'}
              </Text>
            </div>
            {designs && designs.length > 0 && (
              <Button leftSection={<IconUpload size={18} />} onClick={modal.open}>
                Upload
              </Button>
            )}
          </Group>

          {isLoading && (
            <Stack gap="sm">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} height={72} radius="md" />
              ))}
            </Stack>
          )}

          {isError && (
            <Alert
              color="red"
              icon={<IconAlertTriangle size={18} />}
              title="Couldn't load designs"
            >
              <Group justify="space-between">
                <Text size="sm">Something went wrong while fetching designs.</Text>
                <Button size="xs" variant="white" color="red" onClick={() => refetch()}>
                  Retry
                </Button>
              </Group>
            </Alert>
          )}

          {designs && designs.length === 0 && (
            <Center mih="50vh">
              <Stack align="center" gap="sm" maw={380} ta="center">
                <ThemeIcon size={64} radius="xl" variant="light">
                  <IconCloudUpload size={32} />
                </ThemeIcon>
                <Title order={3}>No designs yet</Title>
                <Text c="dimmed" size="sm">
                  Upload an IFC design file to add it to this project.
                </Text>
                <Button
                  size="md"
                  leftSection={<IconUpload size={18} />}
                  onClick={modal.open}
                  mt="xs"
                >
                  Upload design
                </Button>
              </Stack>
            </Center>
          )}

          {designs && designs.length > 0 && (
            <Stack gap="sm">
              {designs.map((d) => (
                <DesignCard key={d.designId} design={d} projectId={projectId} />
              ))}
            </Stack>
          )}

          <UploadModal
            projectId={projectId}
            opened={modalOpened}
            onClose={modal.close}
          />
        </>
      )}
    </Container>
  );
}
