import { useCurrentRoute } from './useCurrentRoute';
import { useBreadcrumbs } from './useBreadcrumbs';
import { usePageTitle } from './usePageTitle';

export const usePageRouteInfo = () => {
  const currentRoute = useCurrentRoute();
  const pageTitle = usePageTitle(currentRoute);
  const breadcrumbs = useBreadcrumbs(currentRoute);

  return {
    pageTitle,
    breadcrumbs,
  };
};
