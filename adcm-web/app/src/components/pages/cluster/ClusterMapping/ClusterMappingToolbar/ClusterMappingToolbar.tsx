import React from 'react';
import s from './ClusterMappingToolbar.module.scss';
import cn from 'classnames';

export interface ClusterMappingToolbarProps extends React.PropsWithChildren {
  className?: string;
}

const ClusterMappingToolbar = ({ className = '', children }: ClusterMappingToolbarProps) => {
  return <div className={cn(s.clusterMappingToolbar, className)}>{children}</div>;
};

export default ClusterMappingToolbar;
