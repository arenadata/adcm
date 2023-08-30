import React, { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { TabsBlock, Tab } from '@uikit';
import s from './ClusterMapping.module.scss';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const ClusterMapping: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Mapping' },
        ]),
      );
    }
  }, [cluster, dispatch]);

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
