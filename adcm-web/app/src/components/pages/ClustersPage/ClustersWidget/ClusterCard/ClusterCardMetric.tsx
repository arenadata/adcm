import type React from 'react';
import { Icon, Tooltip } from '@uikit';
import type { IconsNames } from '@uikit';
import s from './ClusterCard.module.scss';

export interface ClusterCardMetricTooltip {
  label: string;
  icon: IconsNames;
  iconClassName?: string;
}

export interface ClusterCardMetricProps {
  label: string;
  value: React.ReactNode;
  tooltip?: ClusterCardMetricTooltip;
}

const ClusterCardMetric: React.FC<ClusterCardMetricProps> = ({ label, value, tooltip }) => (
  <div className={s.clusterCard__metric}>
    <span className={s.clusterCard__metricLabel}>
      {label}
      {tooltip && (
        <Tooltip label={tooltip.label}>
          <Icon name={tooltip.icon} size={24} className={tooltip.iconClassName ?? s.clusterCard__metricIcon} />
        </Tooltip>
      )}
    </span>
    <span className={s.clusterCard__metricValue}>{value}</span>
  </div>
);

export default ClusterCardMetric;
