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
  '/clusters/:clusterId/services/:serviceId/primary-configuration': {
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
        href: '/clusters/:clusterId/services',
        label: 'Services',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/configuration-groups': {
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
        href: '/clusters/:clusterId/services',
        label: 'Services',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/components': {
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
        href: '/clusters/:clusterId/services',
        label: 'Services',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/info': {
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
        href: '/clusters/:clusterId/services',
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
  '/clusters/:clusterId/mapping/hosts': {
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
  '/clusters/:clusterId/mapping/components': {
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
  '/clusters/:clusterId/import/cluster': {
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
  '/clusters/:clusterId/import/services': {
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
  '/access-manager/policies': {
    pageTitle: 'Policies',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access Manager',
      },
      {
        label: 'Policies',
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
  '/bundles/:bundleId': {
    pageTitle: 'Bundles',
    breadcrumbs: [
      {
        href: '/bundles',
        label: 'Bundles',
      },
      {
        href: '/bundles/:bundleId',
        label: ':bundleId',
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
