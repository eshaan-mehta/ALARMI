import { Button, Center, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router-dom';

export function NotFound() {
  return (
    <Center mih="70vh">
      <Stack align="center" gap="xs" maw={420}>
        <Title order={1} c="violet">
          404
        </Title>
        <Text c="dimmed" ta="center">
          We couldn&apos;t find the page you were looking for.
        </Text>
        <Button component={Link} to="/" mt="sm">
          Back to home
        </Button>
      </Stack>
    </Center>
  );
}
