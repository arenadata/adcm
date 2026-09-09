import s from './ClusterOverviewServiceItem.module.scss';
import { Icon, Statusable, Tooltip } from '@uikit';
import type { AdcmClusterOverviewStatusService } from '@models/adcm';
import { AdcmClusterStatus, AdcmMaintenanceMode } from '@models/adcm';
import { Link } from 'react-router-dom';

interface ClusterOverviewServiceItemProps {
  service: AdcmClusterOverviewStatusService;
  clusterId: number;
}

const ClusterOverviewServiceItem = ({ service, clusterId }: ClusterOverviewServiceItemProps) => {
  const serviceStatus = service.status === AdcmClusterStatus.Up ? 'done' : 'unknown';
  const totalComponentsCount = service.components?.length || 0;
  const activeComponentsCount = service.components?.filter((component) => component.status === 'up').length || 0;
  const isMaintenanceMode = service.maintenanceMode === AdcmMaintenanceMode.On;
  const componentsLabel = totalComponentsCount === 1 ? 'Component' : 'Components';

  return (
    <div className={s.clusterOverviewServiceItem}>
      <div className={s.clusterOverviewServiceItem__header}>
        <Tooltip label={service.displayName}>
          <Statusable
            className={s.clusterOverviewServiceItem__title}
            status={serviceStatus}
            size="medium"
            iconPosition="right"
          >
            <Link to={`/clusters/${clusterId}/services/${service.id}/components`} className="text-link">
              {service.displayName}
            </Link>
          </Statusable>
        </Tooltip>
        {isMaintenanceMode && (
          <Tooltip label="Maintenance mode">
            <Icon name="g1-maintenance" size={20} className={s.clusterOverviewServiceItem__mmIcon} />
          </Tooltip>
        )}
      </div>

      <div className={s.clusterOverviewServiceItem__text}>
        {activeComponentsCount}/{totalComponentsCount} {componentsLabel}
      </div>
    </div>
  );
};

export default ClusterOverviewServiceItem;
