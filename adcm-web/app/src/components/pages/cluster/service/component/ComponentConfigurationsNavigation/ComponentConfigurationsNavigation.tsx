import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';
import { Tab, TabsBlock } from '@uikit';
import React from 'react';
import { Outlet } from 'react-router-dom';

const ComponentConfigurationsNavigation: React.FC = () => {
  return (
    <>
      <SubNavigationWrapper>
        <TabsBlock variant="secondary" dataTest="tab-container-components">
          <Tab to="primary-configuration">Primary configuration</Tab>
          <Tab to="configuration-groups">Configuration groups</Tab>
        </TabsBlock>
      </SubNavigationWrapper>
      <Outlet />
    </>
  );
};

export default ComponentConfigurationsNavigation;
