import type React from 'react';
import ServiceComponentsMaintenanceModeDialog from './ServiceComponentsMaintenanceModeDialog/ServiceComponentsMaintenanceMode';
import ServiceComponentsDynamicActionDialog from './ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';

const ServiceComponentsDialogs: React.FC = () => {
  return (
    <>
      <ServiceComponentsMaintenanceModeDialog />
      <ServiceComponentsDynamicActionDialog />
    </>
  );
};

export default ServiceComponentsDialogs;
