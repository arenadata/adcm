import { RoutesConfigs } from './routes.types';

const routes: RoutesConfigs = {
  // Clusters
  '/clusters': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        label: 'Clusters',
      },
    ],
  },
  '/clusters/:clusterName/overview': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterName',
        label: ':clusterName',
      },
      {
        label: 'Overview',
      },
    ],
  },

  // Hostproviders
  '/hostproviders': {
    pageTitle: 'Hostproviders',
    breadcrumbs: [
      {
        label: 'Hostproviders',
      },
    ],
  },

  // Hosts
  '/hosts': {
    pageTitle: 'Hosts',
    breadcrumbs: [
      {
        label: 'Hosts',
      },
    ],
  },

  // Hosts
  '/jobs': {
    pageTitle: 'Jobs',
    breadcrumbs: [
      {
        label: 'Jobs',
      },
    ],
  },

  // Access Manager
  '/access-manager': {
    pageTitle: 'Access Manager',
    breadcrumbs: [
      {
        label: 'Access Manager',
      },
    ],
  },

  // Audit
  '/audit': {
    pageTitle: 'Audit',
    breadcrumbs: [
      {
        label: 'Audit',
      },
    ],
  },

  // Bundles
  '/bundles': {
    pageTitle: 'Bundles',
    breadcrumbs: [
      {
        label: 'Bundles',
      },
    ],
  },

  // Profile
  '/profile': {
    pageTitle: 'Profile',
    breadcrumbs: [
      {
        label: 'Profile',
      },
    ],
  },

  // Settings
  '/settings': {
    pageTitle: 'Settings',
    breadcrumbs: [
      {
        label: 'Settings',
      },
    ],
  },
};

export default routes;
