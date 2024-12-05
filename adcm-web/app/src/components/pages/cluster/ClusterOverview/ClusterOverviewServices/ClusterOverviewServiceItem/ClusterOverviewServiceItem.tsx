import s from './ClusterOverviewServiceItem.module.scss';
import { Statusable, Tooltip } from '@uikit';
import type { AdcmClusterOverviewStatusService } from '@models/adcm';
import { AdcmClusterStatus } from '@models/adcm';
import { Link } from 'react-router-dom';

interface ClusterOverviewServiceItemProps {
  service: AdcmClusterOverviewStatusService;
  clusterId: number;
}

const ClusterOverviewServiceItem = ({ service, clusterId }: ClusterOverviewServiceItemProps) => {
  const serviceStatus = service.status === AdcmClusterStatus.Up ? 'done' : 'unknown';
  const totalComponentsCount = service.components?.length || 0;
  const activeComponentsCount = service.components?.filter((component) => component.status === 'up').length || 0;

  return (
    <div className={s.clusterOverviewServiceItem}>
      <Tooltip label={service.displayName}>
        <Statusable className={s.clusterOverviewServiceItem__title} status={serviceStatus} size="medium">
          <Link to={`/clusters/${clusterId}/services/${service.id}/components`} className="text-link">
            {service.displayName}
          </Link>
        </Statusable>
      </Tooltip>

      <div className={s.clusterOverviewServiceItem__text}>
        {activeComponentsCount}/{totalComponentsCount} components
      </div>
    </div>
  );
};

export default ClusterOverviewServiceItem;
