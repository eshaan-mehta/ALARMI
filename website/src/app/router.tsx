import { createBrowserRouter } from 'react-router-dom';
import { RootLayout } from './RootLayout';
import { RouteError } from './RouteError';
import { LandingPage } from '../pages/LandingPage';
import { ProjectsDashboard } from '../pages/ProjectsDashboard';
import { ProjectDetail } from '../pages/ProjectDetail';
import { NotFound } from '../pages/NotFound';

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <LandingPage /> },
      {
        path: 'projects',
        children: [
          { index: true, element: <ProjectsDashboard /> },
          { path: ':projectName', element: <ProjectDetail /> },
        ],
      },
      { path: '*', element: <NotFound /> },
    ],
  },
]);
