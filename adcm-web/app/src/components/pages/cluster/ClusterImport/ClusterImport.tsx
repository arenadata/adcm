import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import s from './ClusterImport.module.scss';
import { Tab, TabsBlock } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { RequestState } from '@models/loadState';

const ClusterImport = () => {
  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterImports.accessCheckStatus);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Import' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div className={s.clusterImport}>
      {accessCheckStatus === RequestState.Completed && (
        <TabsBlock variant="secondary" className={s.clusterImport__tabsBlock}>
          <Tab to="cluster">Cluster</Tab>
          <Tab to="services">Services</Tab>
        </TabsBlock>
      )}
      <Outlet />
    </div>
  );
};

export default ClusterImport;
