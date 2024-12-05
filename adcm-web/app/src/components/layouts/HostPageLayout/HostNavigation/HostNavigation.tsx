import type React from 'react';
import { useEffect } from 'react';
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
  const host = useStore(({ adcm }) => adcm.host.host);

  const { pathname } = useLocation();
  const [, , , subTabId] = pathname.split('/');

  useEffect(() => {
    if (host) {
      dispatch(
        setBreadcrumbs([
          { href: '/hosts', label: 'Hosts' },
          { label: host.name },
          { label: tabsNavigationDictionary[subTabId] },
        ]),
      );
    }
  }, [host, subTabId, dispatch]);

  return (
    <SubNavigationWrapper>
      <TabsBlock variant="secondary">
        <Tab to="host-components">Host-Components</Tab>
        <Tab to="primary-configuration">Primary configuration</Tab>
      </TabsBlock>
    </SubNavigationWrapper>
  );
};

export default ClusterHostNavigation;
