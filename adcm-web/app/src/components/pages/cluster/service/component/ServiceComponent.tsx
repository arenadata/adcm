import React from 'react';
import { useRequestServiceComponent } from './useRequestServiceComponent';
import ServiceComponentTable from './ServiceComponentTable/ServiceComponentTable';
import ComponentConfigurationsNavigation from './ComponentConfigurationsNavigation/ComponentConfigurationsNavigation';
import { useStore } from '@hooks';
import { useNavigate } from 'react-router-dom';
import ServiceComponentsDynamicActionDialog from '../ServiceComponents/Dialogs/ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';

const ServiceComponent: React.FC = () => {
  const navigate = useNavigate();

  useRequestServiceComponent();

  const serviceComponent = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);

  const handleClickReturn = () => {
    navigate(`/clusters/${serviceComponent?.cluster.id}/services/${serviceComponent?.service.id}/components`);
  };

  return (
    <>
      <ServiceComponentTable onClick={handleClickReturn} />
      <ComponentConfigurationsNavigation />
      <ServiceComponentsDynamicActionDialog />
    </>
  );
};

export default ServiceComponent;
