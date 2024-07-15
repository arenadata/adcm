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
  '/clusters/:clusterId': {
    pageTitle: 'Clusters',
    breadcrumbs: [
      {
        href: '/clusters',
        label: 'Clusters',
      },
      {
        label: ':clusterId',
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
  '/clusters/:clusterId/services/:serviceId': {
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
      {
        label: ':serviceId',
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
      {
        label: ':serviceId',
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
      {
        label: ':serviceId',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/configuration-groups/:groupId': {
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
      {
        label: 'Configuration groups',
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
      {
        href: '/clusters/:clusterId/services/:serviceId',
        label: ':serviceId',
      },
      {
        label: 'Components',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/components/:componentId/primary-configuration': {
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
      {
        href: '/clusters/:clusterId/services/:serviceId',
        label: ':serviceId',
      },
      {
        href: '/clusters/:clusterId/services/:serviceId/components',
        label: 'Components',
      },
      {
        href: '/clusters/:clusterId/services/:serviceId/components/:componentId',
        label: ':componentId',
      },
      {
        label: 'Primary configuration',
      },
    ],
  },
  '/clusters/:clusterId/services/:serviceId/components/:componentId/configuration-groups': {
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
      {
        href: '/clusters/:clusterId/services/:serviceId',
        label: ':serviceId',
      },
      {
        href: '/clusters/:clusterId/services/:serviceId/components',
        label: 'Components',
      },
      {
        href: '/clusters/:clusterId/services/:serviceId/components/:componentId',
        label: ':componentId',
      },
      {
        label: 'Configuration groups',
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
  '/clusters/:clusterId/hosts/:hostId': {
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
        href: '/clusters/:clusterId/hosts',
        label: 'Hosts',
      },
      {
        label: ':hostId',
      },
    ],
  },
  '/clusters/:clusterId/hosts/:hostId/host-components': {
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
        href: '/clusters/:clusterId/hosts',
        label: 'Hosts',
      },
      {
        href: '/clusters/:clusterId/hosts/:hostId',
        label: ':hostId',
      },
      {
        label: 'host-components',
      },
    ],
  },
  '/clusters/:clusterId/hosts/:hostId/primary-configuration': {
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
        href: '/clusters/:clusterId/hosts',
        label: 'Hosts',
      },
      {
        label: 'primary-configuration',
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
  '/clusters/:clusterId/configuration/primary-configuration': {
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
      {
        label: 'Primary configuration',
      },
    ],
  },
  '/clusters/:clusterId/configuration/config-groups': {
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
        href: '/clusters/:clusterId/configuration',
        label: 'Configuration',
      },
      {
        label: 'Configuration groups',
      },
    ],
  },
  '/clusters/:clusterId/configuration/ansible-settings': {
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
      {
        label: 'Ansible settings',
      },
    ],
  },
  '/clusters/:clusterId/configuration/action-host-groups': {
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
      {
        label: 'Action hosts groups',
      },
    ],
  },
  '/clusters/:clusterId/configuration/config-groups/:groupId': {
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
        href: '/clusters/:clusterId/configuration',
        label: 'Configuration',
      },
      {
        href: '/clusters/:clusterId/configuration/config-groups',
        label: 'Configuration groups',
      },
      {
        label: ':groupId',
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
  '/hostproviders/:hostproviderId/*': {
    pageTitle: 'Hostproviders',
    breadcrumbs: [
      {
        href: '/hostproviders',
        label: 'Hostproviders',
      },
      {
        label: ':hostproviderId',
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
  '/hosts/:hostId/*': {
    pageTitle: 'Hosts',
    breadcrumbs: [
      {
        href: '/hosts',
        label: 'Hosts',
      },
      {
        label: ':hostId',
      },
    ],
  },

  // Jobs
  '/jobs': {
    pageTitle: 'Jobs',
    breadcrumbs: [
      {
        label: 'Jobs',
      },
    ],
  },
  '/jobs/:jobId': {
    pageTitle: 'Jobs',
    breadcrumbs: [
      {
        href: '/jobs',
        label: 'Jobs',
      },
      {
        label: ':jobId',
      },
    ],
  },
  '/jobs/:jobId/:withAutoStop': {
    pageTitle: 'Jobs',
    breadcrumbs: [
      {
        href: '/jobs',
        label: 'Jobs',
      },
      {
        label: ':jobId',
      },
    ],
  },

  // Access manager
  '/access-manager': {
    pageTitle: 'Access manager',
    breadcrumbs: [
      {
        label: 'Access manager',
      },
    ],
  },
  '/access-manager/users': {
    pageTitle: 'Access manager',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access manager',
      },
      {
        label: 'Users',
      },
    ],
  },
  '/access-manager/groups': {
    pageTitle: 'Access manager',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access manager',
      },
      {
        label: 'Groups',
      },
    ],
  },
  '/access-manager/roles': {
    pageTitle: 'Access manager',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access manager',
      },
      {
        label: 'Roles',
      },
    ],
  },
  '/access-manager/policies': {
    pageTitle: 'Access manager',
    breadcrumbs: [
      {
        href: '/access-manager',
        label: 'Access manager',
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
      {
        label: 'General',
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

  // Error
  '*': {
    pageTitle: 'Error',
    breadcrumbs: [
      {
        label: 'Error',
      },
      {
        label: '404',
      },
    ],
  },
};

export default routes;
