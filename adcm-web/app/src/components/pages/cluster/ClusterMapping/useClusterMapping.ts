import { useCallback, useEffect, useMemo, useState } from 'react';
import { AdcmMappingComponent, AdcmHostShortView, AdcmMapping } from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import {
  getComponentsMapping,
  getHostsMapping,
  getServicesMapping,
  mapHostsToComponent,
  validate,
} from './ClusterMapping.utils';
import {
  MappingFilter,
  HostMapping,
  ComponentMapping,
  ServiceMapping,
  HostsDictionary,
  ComponentsDictionary,
} from './ClusterMapping.types';
import { NotAddedServicesDictionary } from '@store/adcm/cluster/mapping/mappingSlice';

export const useClusterMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
) => {
  const hostsDictionary: HostsDictionary = useMemo(() => arrayToHash(hosts, (h) => h.id), [hosts]);
  const componentsDictionary: ComponentsDictionary = useMemo(() => arrayToHash(components, (c) => c.id), [components]);

  const [localMapping, setLocalMapping] = useState<AdcmMapping[]>(mapping);
  const [isMappingChanged, setIsMappingChanged] = useState(false);

  const [mappingFilter, setMappingFilter] = useState<MappingFilter>({
    componentDisplayName: '',
    hostName: '',
    isHideEmpty: false,
  });

  useEffect(() => {
    if (isLoaded) {
      setLocalMapping(mapping);
    }
  }, [isLoaded, mapping]);

  const componentsMapping: ComponentMapping[] = useMemo(
    () => (isLoaded ? getComponentsMapping(localMapping, components, hostsDictionary) : []),
    [components, hostsDictionary, isLoaded, localMapping],
  );

  const hostsMapping: HostMapping[] = useMemo(
    () => (isLoaded ? getHostsMapping(localMapping, hosts, componentsDictionary) : []),
    [hosts, componentsDictionary, isLoaded, localMapping],
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
      setLocalMapping(newLocalMapping);
      setIsMappingChanged(true);
    },
    [servicesMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newMapping = localMapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      setLocalMapping(newMapping);
      setIsMappingChanged(true);
    },
    [localMapping],
  );

  const handleMappingFilterChange = (changes: Partial<MappingFilter>) => {
    setMappingFilter({
      ...mappingFilter,
      ...changes,
    });
  };

  const handleReset = () => {
    setLocalMapping(mapping);
    setIsMappingChanged(false);
  };

  return {
    hosts,
    hostsMapping,
    localMapping,
    isMappingChanged,
    mappingFilter,
    handleMappingFilterChange,
    components,
    servicesMapping,
    mappingValidation,
    handleMap,
    handleUnmap,
    handleReset,
  };
};
