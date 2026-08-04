import {
  ActionIcon,
  Alert,
  Anchor,
  Button,
  Center,
  Container,
  Group,
  Menu,
  Skeleton,
  Stack,
  Text,
  ThemeIcon,
  Title,
  Tooltip,
} from '@mantine/core';
import { useDisclosure } from '@mantine/hooks';
import { modals } from '@mantine/modals';
import { notifications } from '@mantine/notifications';
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconCloudUpload,
  IconDots,
  IconTrash,
  IconUpload,
} from '@tabler/icons-react';
import { isAxiosError } from 'axios';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { DesignCard } from '../components/DesignCard';
import { UploadModal } from '../components/UploadModal';
import { useProjectDesigns } from '../data/designs/hooks';
import { useDeleteProject, useProject } from '../data/projects/hooks';

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
  const navigate = useNavigate();
  const del = useDeleteProject();

  // The projects list resolved but no project has this id.
  const notFound = projectsLoaded && !project;

  // The backend refuses to delete a project while extraction is still running,
  // so the action is held back until every design has settled. This list polls
  // every 2s while anything is processing, so it re-enables on its own.
  const processing = designs?.some((d) => d.status === 'PROCESSING') ?? false;
  const blocked = processing || del.isPending;
  const designCount = designs?.length ?? 0;

  const confirmDelete = () =>
    modals.openConfirmModal({
      title: 'Delete project',
      centered: true,
      children: (
        <Text size="sm">
          Delete “{project?.name}”? This permanently removes the project and
          {designCount === 1 ? ' its design' : ` all ${designCount} of its designs`},
          including every uploaded file and extracted module. This can&apos;t be
          undone.
        </Text>
      ),
      labels: { confirm: 'Delete', cancel: 'Cancel' },
      confirmProps: { color: 'red' },
      onConfirm: () =>
        del.mutate(projectId, {
          onSuccess: () => {
            notifications.show({
              color: 'gray',
              title: 'Project deleted',
              message: `“${project?.name}” and its designs were removed.`,
            });
            navigate('/projects'); // this page no longer exists
          },
          // Covers the 409 raised when a design started processing after the
          // list last polled.
          onError: (err) =>
            notifications.show({
              color: 'red',
              title: "Couldn't delete project",
              message: isAxiosError(err)
                ? (err.response?.data?.message ?? 'Please try again.')
                : 'Please try again.',
            }),
        }),
    });

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
            <Group gap="xs">
              {designs && designs.length > 0 && (
                <Button leftSection={<IconUpload size={18} />} onClick={modal.open}>
                  Upload
                </Button>
              )}
              <Menu position="bottom-end" withinPortal>
                <Menu.Target>
                  <ActionIcon variant="subtle" color="gray" aria-label="Project actions">
                    <IconDots size={18} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Tooltip
                    label="Wait for processing to finish"
                    disabled={!blocked}
                    position="left"
                  >
                    {/* data-disabled, not disabled: a truly disabled button emits
                        no mouse events, so the tooltip explaining why would never
                        open. The click is turned away by hand instead. */}
                    <Menu.Item
                      color="red"
                      data-disabled={blocked || undefined}
                      leftSection={<IconTrash size={16} />}
                      onClick={(event) => {
                        if (blocked) {
                          event.preventDefault();
                          return;
                        }
                        confirmDelete();
                      }}
                    >
                      Delete project
                    </Menu.Item>
                  </Tooltip>
                </Menu.Dropdown>
              </Menu>
            </Group>
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
