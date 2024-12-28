import type React from 'react';
import { useEffect } from 'react';
import { Tab, TabsBlock } from '@uikit';
import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { useLocation } from 'react-router-dom';

const tabsNavigationDictionary: { [key: string]: string } = {
  'primary-configuration': 'Primary configuration',
  'configuration-groups': 'Configuration groups',
};

const HostProviderNavigation: React.FC = () => {
  const dispatch = useDispatch();
  const hostProvider = useStore(({ adcm }) => adcm.hostProvider.hostProvider);

  const { pathname } = useLocation();
  const [, , , subTabId] = pathname.split('/');

  useEffect(() => {
    if (hostProvider) {
      dispatch(
        setBreadcrumbs([
          { href: '/hostproviders', label: 'Hostproviders' },
          { href: `/hostproviders/${hostProvider.id}`, label: hostProvider.name },
          { label: tabsNavigationDictionary[subTabId] },
        ]),
      );
    }
  }, [hostProvider, subTabId, dispatch]);

  return (
    <SubNavigationWrapper>
      <TabsBlock variant="secondary">
        <Tab to="primary-configuration">Primary configuration</Tab>
        <Tab to="configuration-groups">Configuration groups</Tab>
      </TabsBlock>
    </SubNavigationWrapper>
  );
};

export default HostProviderNavigation;
