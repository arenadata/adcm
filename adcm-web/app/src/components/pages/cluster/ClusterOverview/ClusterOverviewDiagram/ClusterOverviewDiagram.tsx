import CircleDiagram from '@uikit/CircleDiagram/CircleDiagram';
import s from './ClusterOverviewDiagram.module.scss';
import { AdcmClusterStatus } from '@models/adcm';

interface ClusterOverviewDiagramProps {
  status: AdcmClusterStatus;
  currentCount: number;
  totalCount: number;
}

const ClusterOverviewDiagram = ({ status, currentCount, totalCount }: ClusterOverviewDiagramProps) => {
  const diagramClass = status === AdcmClusterStatus.Up ? s.clusterOverviewDiagram_up : s.clusterOverviewDiagram_down;

  return (
    <div className={s.clusterOverviewDiagram__wrapper}>
      <CircleDiagram totalCount={totalCount} currentCount={currentCount} colorClass={diagramClass} />
    </div>
  );
};

export default ClusterOverviewDiagram;
