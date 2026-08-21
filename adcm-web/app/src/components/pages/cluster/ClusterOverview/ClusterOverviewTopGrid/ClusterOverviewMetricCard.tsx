import type React from 'react';
import ClusterEntityMetricCard from '@commonComponents/ClusterEntityMetricCard/ClusterEntityMetricCard';
import s from './ClusterOverviewTopGrid.module.scss';

type ClusterOverviewMetricCardProps = {
  title: string;
  up: number;
  down: number;
};

const ClusterOverviewMetricCard: React.FC<ClusterOverviewMetricCardProps> = ({ title, up, down }) => (
  <ClusterEntityMetricCard
    className={s.clusterOverviewTopGrid__card}
    titleClassName={s.clusterOverviewTopGrid__cardTitle}
    title={title}
    up={up}
    down={down}
  />
);

export default ClusterOverviewMetricCard;
