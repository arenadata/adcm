import type React from 'react';
import { useEffect } from 'react';
import { useRequestServiceComponents } from './useRequestServiceComponents';
import ServiceComponentsTable from './ServiceComponentsTable/ServiceComponentsTable';
import ServiceComponentsDialogs from './Dialogs';
import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import ServiceComponentsTableFooter from './ServiceComponentsTableFooter/ServiceComponentsTableFooter';

const ServiceComponents: React.FC = () => {
  const dispatch = useDispatch();
  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  const service = useStore(({ adcm }) => adcm.service.service);

  useEffect(() => {
    if (cluster && service) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/services`, label: 'Services' },
          { href: `/clusters/${cluster.id}/services/${service.id}`, label: service.displayName },
          { label: 'Components' },
        ]),
      );
    }
  }, [cluster, dispatch, service]);

  useRequestServiceComponents();

  return (
    <>
      <ServiceComponentsTable />
      <ServiceComponentsDialogs />
      <ServiceComponentsTableFooter />
    </>
  );
};

export default ServiceComponents;
