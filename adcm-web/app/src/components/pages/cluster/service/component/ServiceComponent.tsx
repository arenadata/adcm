import React, { useState } from 'react';
import { useRequestServiceComponent } from './useRequestServiceComponent';
import ServiceComponentTable from './ServiceComponentTable/ServiceComponentTable';
import ComponentConfigurationsNavigation from './ComponentConfigurationsNavigation/ComponentConfigurationsNavigation';
import { useStore } from '@hooks';
import { useNavigate } from 'react-router-dom';
import ServiceComponentsDynamicActionDialog from '../ServiceComponents/Dialogs/ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';

const ServiceComponent: React.FC = () => {
  const navigate = useNavigate();
  const [isConfigShown, setIsConfigShown] = useState<boolean>(false);

  useRequestServiceComponent();

  const serviceComponent = useStore(({ adcm }) => adcm.serviceComponent.serviceComponent);

  const handleClickComponentName = () => {
    setIsConfigShown(true);
  };

  const handleClickReturn = () => {
    navigate(`/clusters/${serviceComponent?.cluster.id}/services/${serviceComponent?.service.id}/components`);
    setIsConfigShown(false);
  };

  return (
    <>
      <ServiceComponentTable
        isConfigShown={isConfigShown}
        showConfig={handleClickComponentName}
        onClick={handleClickReturn}
      />
      {isConfigShown && <ComponentConfigurationsNavigation />}
      <ServiceComponentsDynamicActionDialog />
    </>
  );
};

export default ServiceComponent;
