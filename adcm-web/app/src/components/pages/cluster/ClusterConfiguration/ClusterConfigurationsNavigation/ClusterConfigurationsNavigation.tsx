import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';
import { Tab, TabsBlock } from '@uikit';
import type React from 'react';

const ClusterConfigurationsNavigation: React.FC = () => {
  return (
    <>
      <SubNavigationWrapper>
        <TabsBlock variant="secondary">
          <Tab to="primary-configuration">Primary configuration</Tab>
          <Tab to="config-groups">Configuration groups</Tab>
          <Tab to="ansible-settings">Ansible settings</Tab>
          <Tab to="action-host-groups">Action host groups</Tab>
        </TabsBlock>
      </SubNavigationWrapper>
    </>
  );
};

export default ClusterConfigurationsNavigation;
