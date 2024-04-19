import CircleDiagram from '@uikit/CircleDiagram/CircleDiagram';
import s from './ClusterOverviewDiagram.module.scss';
import cn from 'classnames';
import { AdcmServiceStatus, AdcmHostStatus } from '@models/adcm';

interface ClusterOverviewDiagramProps {
  currentCount: number;
  totalCount: number;
  status?: AdcmServiceStatus | AdcmHostStatus;
}

const ClusterOverviewDiagram = ({ status, currentCount, totalCount }: ClusterOverviewDiagramProps) => {
  const diagramClass = cn(
    totalCount > 0 ? (status === 'up' ? s.clusterOverviewDiagram_up : s.clusterOverviewDiagram_down) : undefined,
    !status && currentCount > 0 ? s.clusterOverviewDiagram_empty : undefined,
  );

  return (
    <div className={s.clusterOverviewDiagram__wrapper}>
      <CircleDiagram
        totalCount={totalCount}
        currentCount={currentCount}
        className={diagramClass}
        isDoubleMode={!status}
      />
    </div>
  );
};

export default ClusterOverviewDiagram;
