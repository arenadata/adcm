import { useEffect, useState } from 'react';
import { buildBreadcrumbs } from '@utils/breadcrumbsUtils';
import { BreadcrumbsItemConfig, Route } from '@routes/routes.types';

export const useBreadcrumbs = (currentRoute?: Route) => {
  const [breadcrumbs, setBreadcrumbs] = useState<BreadcrumbsItemConfig[]>([]);

  useEffect(() => {
    if (currentRoute) {
      const newBreadcrumbs = buildBreadcrumbs(currentRoute);
      setBreadcrumbs(newBreadcrumbs);
    }
  }, [currentRoute]);

  return breadcrumbs;
};
