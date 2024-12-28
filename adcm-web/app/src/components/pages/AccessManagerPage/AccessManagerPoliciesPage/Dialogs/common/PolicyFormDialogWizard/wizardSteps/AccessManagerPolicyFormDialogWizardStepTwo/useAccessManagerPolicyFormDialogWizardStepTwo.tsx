import { useStore } from '@hooks';
import { useMemo } from 'react';
import { getStatusLabel } from '@utils/humanizationUtils';

export const useAccessManagerPolicyFormDialogWizardStepTwo = () => {
  const objectCandidates = useStore(({ adcm }) => adcm.policies.relatedData.objectCandidates);
  const services = objectCandidates.service;
  const serviceClusters = services;
  const clusters = objectCandidates.cluster;
  const hosts = objectCandidates.host;
  const hostproviders = objectCandidates.provider;

  const clusterOptions = useMemo(() => {
    return clusters.map(({ id, name }) => ({
      value: id,
      label: getStatusLabel(name),
    }));
  }, [clusters]);

  const serviceOptions = useMemo(() => {
    return [
      ...new Map(
        services.map((service) => [
          service.name,
          {
            value: service.name,
            label: service.displayName,
          },
        ]),
      ).values(),
    ];
  }, [services]);

  const hostOptions = useMemo(() => {
    return hosts.map(({ id, name }) => ({
      value: id,
      label: name,
    }));
  }, [hosts]);

  const hostproviderOptions = useMemo(() => {
    return hostproviders.map(({ id, name }) => ({
      value: id,
      label: name,
    }));
  }, [hostproviders]);

  return {
    relatedData: { clusterOptions, serviceOptions, hostOptions, hostproviderOptions, serviceClusters },
  };
};
