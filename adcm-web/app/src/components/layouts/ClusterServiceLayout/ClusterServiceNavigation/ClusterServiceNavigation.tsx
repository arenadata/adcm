import React from 'react';
import { Tab, TabsBlock } from '@uikit';
import SubNavigationWrapper from '@commonComponents/SubNavigationWrapper/SubNavigationWrapper';

const ClusterServiceNavigation: React.FC = () => {
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
