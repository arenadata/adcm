import { useCallback, useEffect, useMemo, useState } from 'react';
import type { AdcmMappingComponent, AdcmHostShortView, AdcmMapping, NotAddedServicesDictionary } from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import {
  getComponentsMapping,
  getHostsMapping,
  getServicesMapping,
  mapHostsToComponent,
  mapComponentsToHost,
  validate,
  getInitiallyMappedHostsDictionary,
  getInitiallyMappedComponentsDictionary,
} from './ClusterMapping.utils';
import type {
  MappingFilter,
  HostMapping,
  ComponentMapping,
  ServiceMapping,
  HostsDictionary,
  ComponentsDictionary,
} from './ClusterMapping.types';
import type { SortDirection } from '@models/table';

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

  const [mappingSortDirection, setMappingSortDirection] = useState<SortDirection>('asc');

  useEffect(() => {
    if (isLoaded) {
      setLocalMapping(mapping);
    }
  }, [isLoaded, mapping]);

  const componentsMapping: ComponentMapping[] = useMemo(
    () => (isLoaded ? getComponentsMapping(localMapping, components, hostsDictionary) : []),
    [components, hostsDictionary, isLoaded, localMapping],
  );

  const hostsMapping: HostMapping[] = useMemo(() => {
    if (!isLoaded) return [];

    return getHostsMapping(localMapping, hosts, componentsDictionary, {
      sortBy: 'name',
      sortDirection: mappingSortDirection,
    });
  }, [hosts, componentsDictionary, isLoaded, localMapping, mappingSortDirection]);

  const servicesMapping: ServiceMapping[] = useMemo(() => {
    if (!isLoaded) return [];

    return getServicesMapping(componentsMapping, { sortBy: 'name', sortDirection: mappingSortDirection });
  }, [isLoaded, componentsMapping, mappingSortDirection]);

  const servicesMappingDictionary = useMemo(
    () => arrayToHash(servicesMapping, (sm) => sm.service.prototype.id),
    [servicesMapping],
  );

  const mappingErrors = useMemo(() => {
    const errors = validate(componentsMapping, {
      servicesMappingDictionary,
      notAddedServicesDictionary,
      allHostsCount: hosts.length,
    });
    for (const mapping of servicesMapping) {
      mapping.hasErrors = mapping.componentsMapping.some((componentMapping) => !!errors[componentMapping.component.id]);
    }
    return errors;
  }, [componentsMapping, servicesMapping, servicesMappingDictionary, notAddedServicesDictionary, hosts.length]);

  const initiallyMappedHosts = useMemo(() => getInitiallyMappedHostsDictionary(mapping), [mapping]);
  const initiallyMappedComponents = useMemo(() => getInitiallyMappedComponentsDictionary(mapping), [mapping]);

  const handleMapHostsToComponent = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => {
      const newLocalMapping = mapHostsToComponent(localMapping, hosts, component);
      setLocalMapping(newLocalMapping);
      setIsMappingChanged(true);
    },
    [localMapping],
  );

  const handleMapComponentsToHost = useCallback(
    (components: AdcmMappingComponent[], host: AdcmHostShortView) => {
      const newLocalMapping = mapComponentsToHost(localMapping, components, host);
      setLocalMapping(newLocalMapping);
      setIsMappingChanged(true);
    },
    [localMapping],
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
    mappingSortDirection,
    handleMappingSortDirectionChange: setMappingSortDirection,
    components,
    servicesMapping,
    mappingErrors,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    handleReset,
    initiallyMappedHosts,
    initiallyMappedComponents,
  };
};
