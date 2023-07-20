import React from 'react';
import { Tab, TabsBlock } from '@uikit';
import ClusterName from './ClusterName/ClusterName';

const ClusterHeader: React.FC = () => {
  return (
    <TabsBlock className="ignore-page-padding">
      <ClusterName />
      <Tab to="overview">Overview</Tab>
      <Tab to="services">Services</Tab>
      <Tab to="hosts">Hosts</Tab>
      <Tab to="mapping">Mapping</Tab>
      <Tab to="configuration">Configuration</Tab>
      <Tab to="import">Import</Tab>
    </TabsBlock>
  );
};
export default ClusterHeader;
