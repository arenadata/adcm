import React from 'react';
import { Button, ButtonGroup } from '@uikit';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import DeleteServiceButton from '@layouts/ClusterServiceLayout/DeleteServiceButton/DeleteServiceButton';
import ServiceName from '@commonComponents/service/ServiceName/ServiceName';

const ClusterServiceHeader: React.FC = () => {
  const service = useStore(({ adcm }) => adcm.service.service);

  return (
    <EntityHeader
      title={orElseGet(service, (service) => (
        <ServiceName service={service} />
      ))}
      subtitle={orElseGet(service?.prototype.version)}
      central={<div>2/2 successful components</div>}
      actions={
        <ButtonGroup>
          <Button iconLeft="g1-actions" variant="secondary">
            Actions
          </Button>
          <DeleteServiceButton />
        </ButtonGroup>
      }
    />
  );
};

export default ClusterServiceHeader;
