import { Container, Group, Text, UnstyledButton } from '@mantine/core';
import { IconViewfinder } from '@tabler/icons-react';
import { Link } from 'react-router-dom';

export function NavigationBar() {
  return (
    <Container size="lg" h="100%">
      <Group h="100%">
        <UnstyledButton component={Link} to="/">
          <Group gap={8}>
            <IconViewfinder size={26} color="var(--mantine-color-violet-6)" />
            <Text fw={800} size="lg" c="var(--mantine-color-text)" lts={1}>
              ALARMI
            </Text>
          </Group>
        </UnstyledButton>
      </Group>
    </Container>
  );
}
