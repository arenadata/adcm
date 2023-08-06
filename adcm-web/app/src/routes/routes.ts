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
  '/clusters/:clusterId/overview': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Overview',
      },
    ],
  },
  '/clusters/:clusterId/services': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Services',
      },
    ],
  },
  '/clusters/:clusterId/hosts': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Hosts',
      },
    ],
  },
  '/clusters/:clusterId/mapping': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Mapping',
      },
    ],
  },
  '/clusters/:clusterId/configuration': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Configuration',
      },
    ],
  },
  '/clusters/:clusterId/import': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        href: '/clusters/:clusterId',
        label: ':clusterId',
      },
      {
        label: 'Import',
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
  '/access-manager/users': {
    pageTitle: 'Access Manager',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access Manager',
      },
      {
        label: 'Users',
      },
    ],
  },
  '/access-manager/groups': {
    pageTitle: 'Groups',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access Manager',
      },
      {
        label: 'Groups',
      },
    ],
  },
  '/access-manager/roles': {
    pageTitle: 'Roles',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access Manager',
      },
      {
        label: 'Roles',
      },
    ],
  },
  '/access-manager/policy': {
    pageTitle: 'Policy',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access Manager',
      },
      {
        label: 'Policy',
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
  '/audit/operations': {
    pageTitle: 'Audit',
    breadcrumbs: [
      {
        label: 'Audit',
      },
      {
        label: 'Operations',
      },
    ],
  },
  '/audit/logins': {
    pageTitle: 'Audit',
    breadcrumbs: [
      {
        label: 'Audit',
      },
      {
        label: 'Logins',
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
