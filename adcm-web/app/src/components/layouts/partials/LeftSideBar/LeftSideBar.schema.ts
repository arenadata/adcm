import type { IconsNames } from '@uikit';

interface LeftSideBarSchema {
  icon: IconsNames;
  label: string;
  link: string;
}

export const sideBarTopGroup: LeftSideBarSchema[] = [
  {
    label: 'Clusters',
    icon: 'g2-cluster3',
    link: '/clusters',
  },
  {
    label: 'Hostproviders',
    icon: 'g2-provider',
    link: '/hostproviders',
  },
  {
    label: 'Hosts',
    icon: 'g2-hosts',
    link: '/hosts',
  },
  {
    label: 'Jobs',
    icon: 'g2-jobs',
    link: '/jobs',
  },
  {
    label: 'Access manager',
    icon: 'g2-users',
    link: '/access-manager',
  },
  {
    label: 'Audit',
    icon: 'g2-audit',
    link: '/audit',
  },
  {
    label: 'Bundles',
    icon: 'g2-bundles',
    link: '/bundles',
  },
];
