import {
  Badge,
  Button,
  Container,
  Group,
  SimpleGrid,
  Stack,
  Text,
  ThemeIcon,
  Title,
} from '@mantine/core';
import {
  IconArrowRight,
  IconCube,
  IconDeviceMobile,
  IconFileUpload,
  IconRobot,
} from '@tabler/icons-react';
import { useNavigate } from 'react-router-dom';

const steps = [
  {
    icon: IconFileUpload,
    title: 'Upload IFC',
    text: 'Drop in an IFC design file for a room and its modular components.',
  },
  {
    icon: IconCube,
    title: 'Process',
    text: 'The backend extracts module metadata and builds AR-ready models.',
  },
  {
    icon: IconDeviceMobile,
    title: 'Preview in AR',
    text: 'Workers view components at full 1:1 scale anchored in the real room.',
  },
  {
    icon: IconRobot,
    title: 'Robot marks floor',
    text: 'Confirmed placement becomes physical floor-marking instructions.',
  },
];

export function LandingPage() {
  const navigate = useNavigate();

  return (
    <Container size="lg" py={80}>
      <Stack align="center" gap="lg" ta="center">
        <Badge size="lg" variant="light" radius="sm">
          Autonomous Layout &amp; Augmented Reality for Modular Installation
        </Badge>
        <Title order={1} fz={{ base: 40, sm: 60 }} lh={1.05} maw={820}>
          Bring modular designs from{' '}
          <Text span inherit c="violet">
            IFC file
          </Text>{' '}
          to the{' '}
          <Text span inherit c="violet">
            real floor
          </Text>
          .
        </Title>
        <Text size="xl" c="dimmed" maw={640}>
          ALARMI converts IFC design files into AR-compatible models and robot
          marking instructions, so installation crews get the layout right the
          first time.
        </Text>
        <Button
          size="lg"
          radius="md"
          rightSection={<IconArrowRight size={20} />}
          onClick={() => navigate('/projects')}
          mt="sm"
        >
          Get started
        </Button>
      </Stack>

      <SimpleGrid cols={{ base: 1, sm: 2, md: 4 }} spacing="lg" mt={80}>
        {steps.map((s) => (
          <Stack key={s.title} gap="xs">
            <ThemeIcon size={44} radius="md" variant="light">
              <s.icon size={24} />
            </ThemeIcon>
            <Group gap={6}>
              <Text fw={600}>{s.title}</Text>
            </Group>
            <Text size="sm" c="dimmed">
              {s.text}
            </Text>
          </Stack>
        ))}
      </SimpleGrid>
    </Container>
  );
}
