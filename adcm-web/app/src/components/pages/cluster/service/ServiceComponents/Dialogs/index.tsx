import type React from 'react';
import ServiceComponentsMaintenanceModeDialog from './ServiceComponentsMaintenanceModeDialog/ServiceComponentsMaintenanceMode';
import ServiceComponentsDynamicActionDialog from './ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';
import ServiceComponentsActionWizardDialog from '@pages/cluster/service/ServiceComponents/Dialogs/ServiceComponentsDynamicActionWizardDialog/ServiceComponentsDynamicActionWizardDialog';

const ServiceComponentsDialogs: React.FC = () => {
  return (
    <>
      <ServiceComponentsMaintenanceModeDialog />
      <ServiceComponentsDynamicActionDialog />
      <ServiceComponentsActionWizardDialog />
    </>
  );
};

export default ServiceComponentsDialogs;
