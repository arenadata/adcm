import React from 'react';
import { IconButton } from '@uikit';
import s from './ClusterName.module.scss';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';

const ClusterName: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  return (
    <div className={s.clusterName}>
      <div className={s.clusterName__name}>{orElseGet(cluster?.name)}</div>
      <IconButton icon="g1-actions" size={24} />
    </div>
  );
};
export default ClusterName;
