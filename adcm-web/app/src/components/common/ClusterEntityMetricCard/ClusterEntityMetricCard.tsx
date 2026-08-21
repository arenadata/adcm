import type React from 'react';
import cn from 'classnames';
import CircleDiagram from '@uikit/CircleDiagram/CircleDiagram';
import s from './ClusterEntityMetricCard.module.scss';

type ClusterEntityMetricCardProps = {
  title: string;
  up: number;
  down: number;
  className?: string;
  titleClassName?: string;
};

const ClusterEntityMetricCard: React.FC<ClusterEntityMetricCardProps> = ({
  title,
  up,
  down,
  className,
  titleClassName,
}) => (
  <div className={cn(s.clusterEntityMetricCard, className)}>
    <span className={cn(s.clusterEntityMetricCard__title, titleClassName)}>{title}</span>
    <CircleDiagram up={up} down={down} size="medium" />
    <div className={s.clusterEntityMetricCard__legend}>
      <span className={s.clusterEntityMetricCard__legendItem}>
        <span className={cn(s.clusterEntityMetricCard__dot, s.clusterEntityMetricCard__dot_down)} />
        Down <span className={s.clusterEntityMetricCard__legendCount}>{down}</span>
      </span>
      <span className={s.clusterEntityMetricCard__legendItem}>
        <span className={cn(s.clusterEntityMetricCard__dot, s.clusterEntityMetricCard__dot_up)} />
        Up <span className={s.clusterEntityMetricCard__legendCount}>{up}</span>
      </span>
    </div>
  </div>
);

export default ClusterEntityMetricCard;
