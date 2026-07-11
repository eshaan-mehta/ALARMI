import { Button, Center, Stack, Text, Title } from '@mantine/core';
import { Link, useRouteError } from 'react-router-dom';

export function RouteError() {
  const error = useRouteError();
  const message =
    error instanceof Error ? error.message : 'An unexpected error occurred.';

  return (
    <Center mih="70vh">
      <Stack align="center" gap="sm" maw={420}>
        <Title order={2}>Something went wrong</Title>
        <Text c="dimmed" ta="center">
          {message}
        </Text>
        <Button component={Link} to="/" mt="sm">
          Back to home
        </Button>
      </Stack>
    </Center>
  );
}
