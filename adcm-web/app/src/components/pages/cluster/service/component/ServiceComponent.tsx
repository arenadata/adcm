import type React from 'react';
import { useRequestServiceComponent } from './useRequestServiceComponent';
import ServiceComponentTable from './ServiceComponentTable/ServiceComponentTable';
import ComponentConfigurationsNavigation from './ComponentConfigurationsNavigation/ComponentConfigurationsNavigation';
import ServiceComponentsDynamicActionDialog from '../ServiceComponents/Dialogs/ServiceComponentsDynamicActionDialog/ServiceComponentsDynamicActionDialog';
import ServiceComponentsDynamicActionWizardDialog from '@pages/cluster/service/ServiceComponents/Dialogs/ServiceComponentsDynamicActionWizardDialog/ServiceComponentsDynamicActionWizardDialog.tsx';

const ServiceComponent: React.FC = () => {
  useRequestServiceComponent();

  return (
    <>
      <ServiceComponentTable />
      <ComponentConfigurationsNavigation />
      <ServiceComponentsDynamicActionDialog />
      <ServiceComponentsDynamicActionWizardDialog />
    </>
  );
};

export default ServiceComponent;
