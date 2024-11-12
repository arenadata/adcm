import { useMemo } from 'react';
import { buildBreadcrumbs } from '@utils/breadcrumbsUtils';
import type { Route } from '@routes/routes.types';

export const useBreadcrumbs = (currentRoute?: Route) => {
  const breadcrumbs = useMemo(() => {
    if (currentRoute) {
      return buildBreadcrumbs(currentRoute);
    }
    return [];
  }, [currentRoute]);

  return breadcrumbs;
};
