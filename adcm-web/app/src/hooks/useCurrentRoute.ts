import { useMemo } from 'react';
import { useLocation, matchRoutes } from 'react-router-dom';
import routes from '@routes/routes';

const pagesRoutes = Object.keys(routes).map((path: string) => ({ path }));

export const useCurrentRoute = () => {
  const { pathname } = useLocation();

  const currentRoute = useMemo(() => {
    const matchedRoutes = matchRoutes(pagesRoutes, pathname);
    if (!matchedRoutes?.length || !matchedRoutes[0]?.route.path) return;

    return {
      path: matchedRoutes[0].route.path,
      params: matchedRoutes[0].params,
    };
  }, [pathname]);

  return currentRoute;
};
