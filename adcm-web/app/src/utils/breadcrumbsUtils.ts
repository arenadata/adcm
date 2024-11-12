import { generatePath } from 'react-router-dom';
import type { BreadcrumbsItemConfig, DynamicParameters, Route } from '@routes/routes.types';
import routes from '@routes/routes';

const buildPathBreadcrumbs = (path: string, dynamicParams: DynamicParameters): BreadcrumbsItemConfig[] => {
  const parts = routes[path];
  if (!parts) {
    console.error(`breadcrumbs are not defined for path ${path}`);
    return [];
  }

  const breadcrumbs: BreadcrumbsItemConfig[] = [];

  for (const part of parts.breadcrumbs) {
    const crumbs = {} as BreadcrumbsItemConfig;

    if (part.href) {
      crumbs.href = generatePath(part.href, dynamicParams);
    }

    if (part.label) {
      crumbs.label = generatePath(part.label, dynamicParams);
    }

    if (Object.keys(crumbs).length) {
      breadcrumbs.push(crumbs);
    }
  }

  return breadcrumbs;
};

export const buildBreadcrumbs = (route: Route): BreadcrumbsItemConfig[] => {
  return buildPathBreadcrumbs(route.path, route.params);
};
