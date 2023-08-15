import React from 'react';
import { Outlet } from 'react-router-dom';
import s from './ClusterImport.module.scss';
import { Tab, TabsBlock } from '@uikit';

const ClusterImport = () => {
  return (
    <div className={s.clusterImport}>
      <TabsBlock variant="secondary" className={s.clusterImport__tabsBlock}>
        <Tab to="cluster">Cluster</Tab>
        <Tab to="services">Services</Tab>
      </TabsBlock>
      <Outlet />
    </div>
  );
};

export default ClusterImport;
