import { useCallback, useMemo, useState } from 'react';
import { AdcmMappingComponent, AdcmHostShortView, AdcmMapping, AdcmServicePrototype } from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import {
  getComponentsMapping,
  getHostsMapping,
  getServicesMapping,
  mapHostsToComponent,
  validate,
} from './ClusterMapping.utils';
import {
  HostMappingFilter,
  HostMapping,
  ComponentMapping,
  ServiceMappingFilter,
  ServiceMapping,
  HostsDictionary,
  ComponentsDictionary,
} from './ClusterMapping.types';

export const useClusterMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: Record<number, AdcmServicePrototype>,
  isLoaded: boolean,
  handleSetMapping?: (newMapping: AdcmMapping[]) => void,
) => {
  const hostsDictionary: HostsDictionary = useMemo(() => arrayToHash(hosts, (h) => h.id), [hosts]);
  const componentsDictionary: ComponentsDictionary = useMemo(() => arrayToHash(components, (c) => c.id), [components]);

  const [hostsMappingFilter, setHostsMappingFilter] = useState<HostMappingFilter>({
    componentDisplayName: '',
    isHideEmptyHosts: false,
  });
  const [servicesMappingFilter, setServicesMappingFilter] = useState<ServiceMappingFilter>({
    hostName: '',
    isHideEmptyComponents: false,
  });

  const componentsMapping: ComponentMapping[] = useMemo(
    () => (isLoaded ? getComponentsMapping(mapping, components, hostsDictionary) : []),
    [components, hostsDictionary, isLoaded, mapping],
  );

  const hostsMapping: HostMapping[] = useMemo(
    () => (isLoaded ? getHostsMapping(mapping, hosts, componentsDictionary) : []),
    [isLoaded, mapping, hosts, componentsDictionary],
  );

  const servicesMapping: ServiceMapping[] = useMemo(
    () => (isLoaded ? getServicesMapping(componentsMapping) : []),
    [isLoaded, componentsMapping],
  );

  const servicesMappingDictionary = useMemo(
    () => arrayToHash(servicesMapping, (sm) => sm.service.prototype.id),
    [servicesMapping],
  );

  const mappingValidation = useMemo(() => {
    return validate(componentsMapping, {
      servicesMappingDictionary,
      notAddedServicesDictionary,
      allHostsCount: hosts.length,
    });
  }, [componentsMapping, servicesMappingDictionary, notAddedServicesDictionary, hosts.length]);

  const handleMap = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => {
      const newLocalMapping = mapHostsToComponent(servicesMapping, hosts, component);
      handleSetMapping?.(newLocalMapping);
    },
    [servicesMapping, handleSetMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newMapping = mapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      handleSetMapping?.(newMapping);
    },
    [mapping, handleSetMapping],
  );

  const handleServicesMappingFilterChange = (changes: Partial<ServiceMappingFilter>) => {
    setServicesMappingFilter({
      ...servicesMappingFilter,
      ...changes,
    });
  };

  const handleHostsMappingFilterChange = (changes: Partial<HostMappingFilter>) => {
    setHostsMappingFilter({
      ...hostsMappingFilter,
      ...changes,
    });
  };

  return {
    hostComponentMapping: mapping,
    hosts,
    hostsMapping,
    hostsMappingFilter,
    handleHostsMappingFilterChange,
    components,
    servicesMapping,
    servicesMappingFilter,
    handleServicesMappingFilterChange,
    mappingValidation,
    handleMap,
    handleUnmap,
  };
};
