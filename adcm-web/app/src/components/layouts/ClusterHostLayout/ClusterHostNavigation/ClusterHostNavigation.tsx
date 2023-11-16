import React, { useEffect } from 'react';
import { Tab, TabsBlock } from '@uikit';
import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useLocation } from 'react-router-dom';

const tabsNavigationDictionary: { [key: string]: string } = {
  'host-components': 'Host-Components',
  'primary-configuration': 'Primary configuration',
};

const ClusterHostNavigation: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const clusterHost = useStore(({ adcm }) => adcm.clusterHost.clusterHost);

  const { pathname } = useLocation();
  const [, , , , , subTabId] = pathname.split('/');

  useEffect(() => {
    if (cluster && clusterHost) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${clusterHost.id}/hosts`, label: 'Hosts' },
          { label: clusterHost.name },
          { label: tabsNavigationDictionary[subTabId] },
        ]),
      );
    }
  }, [cluster, clusterHost, subTabId, dispatch]);

  return (
    <SubNavigationWrapper>
      <TabsBlock variant="secondary" dataTest="tab-sub-container">
        <Tab to="host-components">Host-Components</Tab>
        <Tab to="primary-configuration">Primary configuration</Tab>
      </TabsBlock>
    </SubNavigationWrapper>
  );
};

export default ClusterHostNavigation;
