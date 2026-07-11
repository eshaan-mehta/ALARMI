import {
  Alert,
  Anchor,
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

export function ProjectDetail() {
  const { projectName = '' } = useParams();
  const decodedName = decodeURIComponent(projectName);
  const { data: designs, isLoading, isError, refetch } = useProjectDesigns(decodedName);
  const [modalOpened, modal] = useDisclosure(false);

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

      <Group justify="space-between" mb="xl" align="flex-end">
        <div>
          <Title order={2}>{decodedName}</Title>
          <Text c="dimmed" size="sm">
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
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} height={180} radius="md" />
          ))}
        </SimpleGrid>
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
        <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="lg">
          {designs.map((d) => (
            <DesignCard key={d.designId} design={d} projectName={decodedName} />
          ))}
        </SimpleGrid>
      )}

      <UploadModal
        projectName={decodedName}
        opened={modalOpened}
        onClose={modal.close}
      />
    </Container>
  );
}
