import React from 'react';
import { Outlet } from 'react-router-dom';
import { TabsBlock, Tab } from '@uikit';
import s from './ClusterMapping.module.scss';

const ClusterMapping: React.FC = () => {
  return (
    <div className={s.clusterMapping}>
      <TabsBlock variant="secondary" className={s.clusterMapping__tabBlocks}>
        <Tab to="hosts">Hosts</Tab>
        <Tab to="components">Components</Tab>
      </TabsBlock>
      <Outlet />
    </div>
  );
};

export default ClusterMapping;
