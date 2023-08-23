import React from 'react';
import { useRequestServiceComponents } from './useRequestServiceComponents';
import ServiceComponentsTable from './ServiceComponentsTable/ServiceComponentsTable';
import ServiceComponentsDialogs from './Dialogs';

const ServiceComponents: React.FC = () => {
  useRequestServiceComponents();

  return (
    <>
      <ServiceComponentsTable />
      <ServiceComponentsDialogs />
    </>
  );
};

export default ServiceComponents;
