import React from 'react';
import { useRequestServiceComponent } from './useRequestServiceComponent';
import ServiceComponentTable from './ServiceComponentTable/ServiceComponentTable';
import ComponentConfigurationsNavigation from './ComponentConfigurationsNavigation/ComponentConfigurationsNavigation';
import ServiceComponentsDynamicActionDialog from '../ServiceComponents/Dialogs/ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';

const ServiceComponent: React.FC = () => {
  useRequestServiceComponent();

  return (
    <>
      <ServiceComponentTable />
      <ComponentConfigurationsNavigation />
      <ServiceComponentsDynamicActionDialog />
    </>
  );
};

export default ServiceComponent;
