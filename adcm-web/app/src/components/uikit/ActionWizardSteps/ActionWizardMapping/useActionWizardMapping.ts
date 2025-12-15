import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import { useDispatch } from '@hooks';
import type {
  ComponentMapping,
  ComponentsDictionary,
  HostMapping,
  HostsDictionary,
  MappingFilter,
  ServiceMapping,
} from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { arrayToHash } from '@utils/arrayUtils';
import type { SortDirection } from '@models/table';
import {
  getComponentsMapping,
  getHostsMapping,
  getServicesMapping,
  mapComponentsToHost,
  mapHostsToComponent,
  validate,
} from '@pages/cluster/ClusterMapping/ClusterMapping.utils';
import {
  cleanupClustersWizardMapping,
  setHostComponentMapDelta,
} from '@store/adcm/clusters/clustersWizardMappingSlice';

export const useActionWizardMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
) => {
  const dispatch = useDispatch();
  const hostsDictionary: HostsDictionary = useMemo(() => arrayToHash(hosts, (h) => h.id), [hosts]);
  const componentsDictionary: ComponentsDictionary = useMemo(() => arrayToHash(components, (c) => c.id), [components]);

  const [localMapping, setLocalMapping] = useState<AdcmMapping[]>(mapping);

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

  useEffect(() => {
    dispatch(setHostComponentMapDelta(getMappingChanges()));
  }, [localMapping]);

  useEffect(() => {
    return () => {
      dispatch(cleanupClustersWizardMapping());
    };
  }, [dispatch]);

  const getMappingChanges = useCallback(() => {
    // Create sets for quick lookups using a unique key per pair
    const originalSet = new Set(mapping.map((m) => `${m.hostId}-${m.componentId}`));
    const currentSet = new Set(localMapping.map((m) => `${m.hostId}-${m.componentId}`));

    // Filter for added: in local but not in original
    const add = localMapping
      .filter((m) => !originalSet.has(`${m.hostId}-${m.componentId}`))
      .map(({ hostId, componentId }) => ({ hostId, componentId }));

    // Filter for removed: in original but not in local
    const remove = mapping
      .filter((m) => !currentSet.has(`${m.hostId}-${m.componentId}`))
      .map(({ hostId, componentId }) => ({ hostId, componentId }));

    return { add, remove };
  }, [mapping, localMapping]);

  const componentsMapping: ComponentMapping[] = useMemo(
    () => (isLoaded ? getComponentsMapping(localMapping, components, hostsDictionary) : []),
    [components, hostsDictionary, isLoaded, localMapping],
  );

  const hostsMapping: HostMapping[] = useMemo(() => {
    const result = isLoaded ? getHostsMapping(localMapping, hosts, componentsDictionary) : [];
    result.sort((a, b) => a.host.name.localeCompare(b.host.name));
    if (mappingSortDirection === 'desc') {
      result.reverse();
    }
    return result;
  }, [hosts, componentsDictionary, isLoaded, localMapping, mappingSortDirection]);

  const servicesMapping: ServiceMapping[] = useMemo(() => {
    const result = isLoaded ? getServicesMapping(componentsMapping) : [];
    if (mappingSortDirection === 'desc') {
      result.reverse();
    }
    return result;
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

  const handleMapHostsToComponent = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => {
      const newLocalMapping = mapHostsToComponent(localMapping, hosts, component);
      setLocalMapping(newLocalMapping);
    },
    [localMapping],
  );

  const handleMapComponentsToHost = useCallback(
    (components: AdcmMappingComponent[], host: AdcmHostShortView) => {
      const newLocalMapping = mapComponentsToHost(localMapping, components, host);
      setLocalMapping(newLocalMapping);
    },
    [localMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newMapping = localMapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      setLocalMapping(newMapping);
    },
    [localMapping],
  );

  const handleMappingFilterChange = (changes: Partial<MappingFilter>) => {
    setMappingFilter({
      ...mappingFilter,
      ...changes,
    });
  };

  return {
    hosts,
    hostsMapping,
    localMapping,
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
  };
};
