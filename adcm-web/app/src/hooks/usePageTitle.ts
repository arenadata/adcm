import routes from '@routes/routes';
import type { Route } from '@routes/routes.types';

export const usePageTitle = (currentRoute?: Route): string => {
  const path = currentRoute?.path;
  return path ? routes[path]?.pageTitle : '';
};
