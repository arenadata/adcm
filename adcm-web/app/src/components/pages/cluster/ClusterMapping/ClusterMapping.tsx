import React, { useEffect } from 'react';
import { Outlet, useParams } from 'react-router-dom';
import { TabsBlock, Tab } from '@uikit';
import s from './ClusterMapping.module.scss';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import { getMappings, cleanupMappings, getNotAddedServices } from '@store/adcm/cluster/mapping/mappingSlice';

const ClusterMapping: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  useEffect(() => {
    if (!Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
      dispatch(getNotAddedServices({ clusterId }));
    }

    return () => {
      dispatch(cleanupMappings());
    };
  }, [clusterId, dispatch]);

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
        <Tab to="components">Components</Tab>
        <Tab to="hosts">Hosts view</Tab>
      </TabsBlock>
      <Outlet />
    </div>
  );
};

export default ClusterMapping;
