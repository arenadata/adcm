import { useMemo } from 'react';
import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import { useMappingEditor } from '@hooks/useMappingEditor';
import type { MappingLayoutKind, MappingViewConfig } from '@utils/mapping/mapping.types';

export const useClusterMappingV2 = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
  kind: MappingLayoutKind = 'services',
) => {
  const viewConfig = useMemo((): MappingViewConfig => {
    return {
      strategy: { type: 'cluster' },
      kind,
      sort: 'name',
    };
  }, [kind]);

  const editor = useMappingEditor(mapping, hosts, components, notAddedServicesDictionary, isLoaded, viewConfig);

  const servicesMapping = editor.viewModel?.kind === 'services' ? editor.viewModel.services : editor.servicesMapping;
  const hostsMapping = editor.viewModel?.kind === 'hosts' ? editor.viewModel.hosts : editor.hostsMapping;

  return {
    ...editor,
    servicesMapping,
    hostsMapping,
  };
};
