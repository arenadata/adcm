import React from 'react';
import { IconButton } from '@uikit';
import s from './ClusterName.module.scss';

const ClusterName: React.FC = () => {
  return (
    <div className={s.clusterName}>
      <div className={s.clusterName__name}>Cluster Name</div>
      <IconButton icon="g1-actions" size={24} />
    </div>
  );
};
export default ClusterName;
