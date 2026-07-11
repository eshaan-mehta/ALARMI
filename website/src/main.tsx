import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import '@mantine/core/styles.css';
import '@mantine/dropzone/styles.css';
import '@mantine/notifications/styles.css';
import './index.css';

import { AppProviders } from './app/providers';
import { router } from './app/router';
import { env } from './lib/env';

/** Start the in-browser mock backend before rendering (dev only). */
async function enableMocking() {
  if (!env.useMocks) return;
  const { worker } = await import('./data/mocks/browser');
  await worker.start({ onUnhandledRequest: 'bypass' });
}

enableMocking().then(() => {
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    </StrictMode>,
  );
});
