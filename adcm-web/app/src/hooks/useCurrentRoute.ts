import { useEffect, useState } from 'react';
import { useLocation, matchRoutes } from 'react-router-dom';
import routes from '@routes/routes';
import { Route } from '@routes/routes.types';

const pagesRoutes = Object.keys(routes).map((path: string) => ({ path }));

export const useCurrentRoute = () => {
  const { pathname } = useLocation();
  const [currentRoute, setCurrentRoute] = useState<Route>();

  useEffect(() => {
    const matchedRoutes = matchRoutes(pagesRoutes, pathname);
    if (matchedRoutes?.length && matchedRoutes[0]?.route.path) {
      const newCurrentRoute = {
        path: matchedRoutes[0].route.path,
        params: matchedRoutes[0].params,
      };

      setCurrentRoute(newCurrentRoute);
    }
  }, [pathname]);

  return currentRoute;
};
