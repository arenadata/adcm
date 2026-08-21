import type React from 'react';
import s from './ClusterOverviewInfoCard.module.scss';

type ClusterOverviewInfoItem = {
  label: string;
  value: React.ReactNode;
};

type ClusterOverviewInfoCardProps = {
  title: string;
  items: ClusterOverviewInfoItem[];
};

const ClusterOverviewInfoCard: React.FC<ClusterOverviewInfoCardProps> = ({ title, items }) => (
  <div className={s.clusterOverviewInfoCard}>
    <span className={s.clusterOverviewInfoCard__title}>{title}</span>
    <div className={s.clusterOverviewInfoCard__table}>
      {items.map(({ label, value }) => (
        <div key={label} className={s.clusterOverviewInfoCard__row}>
          <div className={s.clusterOverviewInfoCard__cell}>{label}</div>
          <div className={s.clusterOverviewInfoCard__cell}>{value}</div>
        </div>
      ))}
    </div>
  </div>
);

export default ClusterOverviewInfoCard;
