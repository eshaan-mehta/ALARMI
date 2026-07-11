import { AppShell } from '@mantine/core';
import { Outlet } from 'react-router-dom';
import { NavigationBar } from '../components/NavigationBar';

export function RootLayout() {
  return (
    <AppShell header={{ height: 60 }} padding="md">
      <AppShell.Header>
        <NavigationBar />
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
