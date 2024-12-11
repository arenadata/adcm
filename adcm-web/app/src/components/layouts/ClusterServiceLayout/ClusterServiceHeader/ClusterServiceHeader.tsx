import type React from 'react';
import { ButtonGroup } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import DeleteServiceButton from '@layouts/ClusterServiceLayout/DeleteServiceButton/DeleteServiceButton';
import ServiceName from './ServiceName/ServiceName';
import ClusterServiceDynamicActionsButton from '@pages/cluster/ClusterServices/ClusterServiceDynamicActionsButton/ClusterServiceDynamicActionsButton';

const ClusterServiceHeader: React.FC = () => {
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);
  const successfulComponentsCount = useStore(({ adcm }) => adcm.service.relatedData.successfulComponentsCount);
  const totalComponentsCount = useStore(({ adcm }) => adcm.service.relatedData.totalComponentsCount);

  return (
    <EntityHeader
      title={orElseGet(service, (service) => <ServiceName service={service} />)}
      central={
        <>
          <span>{orElseGet(service?.prototype.version)}</span>
          <span>
            {successfulComponentsCount} / {totalComponentsCount} successful components
          </span>
        </>
      }
      actions={
        <ButtonGroup>
          {cluster && service && <ClusterServiceDynamicActionsButton cluster={cluster} service={service} />}
          <DeleteServiceButton />
        </ButtonGroup>
      }
    />
  );
};

export default ClusterServiceHeader;
