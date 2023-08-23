import React, { useEffect } from 'react';
import { Tab, TabsBlock } from '@uikit';
import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useLocation } from 'react-router-dom';

const tabsNavigationDictionary: { [key: string]: string } = {
  'primary-configuration': 'Primary Configuration',
  'configuration-groups': 'Configuration Groups',
  components: 'Components',
  info: 'Info',
};

const ClusterServiceNavigation: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);

  const { pathname } = useLocation();
  const [, , , , , subTabId] = pathname.split('/');

  useEffect(() => {
    if (cluster && service) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/services`, label: 'Services' },
          { label: service.displayName },
          { label: tabsNavigationDictionary[subTabId] },
        ]),
      );
    }
  }, [cluster, service, subTabId, dispatch]);

  return (
    <SubNavigationWrapper>
      <TabsBlock variant="secondary">
        <Tab to="primary-configuration">Primary Configuration</Tab>
        <Tab to="configuration-groups">Configuration groups</Tab>
        <Tab to="components">Components</Tab>
        <Tab to="info">Info</Tab>
      </TabsBlock>
    </SubNavigationWrapper>
  );
};

export default ClusterServiceNavigation;
