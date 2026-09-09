import { Statusable } from '@uikit';
import type { AdcmClusterOverviewStatusHost } from '@models/adcm';
import { AdcmClusterStatus } from '@models/adcm';
import { Link } from 'react-router-dom';
import s from './ClusterOverviewHostItem.module.scss';

interface ClusterOverviewHostItemProps {
  host: AdcmClusterOverviewStatusHost;
  clusterId: number;
}

const ClusterOverviewHostItem = ({ host, clusterId }: ClusterOverviewHostItemProps) => {
  const hostStatus = host.status === AdcmClusterStatus.Up ? 'done' : 'unknown';
  const hostName = host.displayName || host.name;

  return (
    <div className={s.clusterOverviewHostItem}>
      <Statusable className={s.clusterOverviewHostItem__title} status={hostStatus} size="medium" iconPosition="right">
        <Link to={`/clusters/${clusterId}/hosts/${host.id}`} className="text-link">
          {hostName}
        </Link>
      </Statusable>
    </div>
  );
};

export default ClusterOverviewHostItem;
