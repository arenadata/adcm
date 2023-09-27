import { useCallback, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { setLocalMapping } from '@store/adcm/cluster/mapping/mappingSlice';
import { AdcmComponent, AdcmHostShortView } from '@models/adcm';
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

export const useClusterMapping = () => {
  const dispatch = useDispatch();

  const {
    hosts,
    components,
    mapping: originalMapping,
    localMapping,
    isLoaded,
    isLoading,
    hasSaveError,
  } = useStore(({ adcm }) => adcm.clusterMapping);

  const [isMappingChanged, setIsMappingChanged] = useState(false);

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
    () => (isLoaded ? getComponentsMapping(localMapping, components, hostsDictionary) : []),
    [components, hostsDictionary, isLoaded, localMapping],
  );

  const hostsMapping: HostMapping[] = useMemo(
    () => (isLoaded ? getHostsMapping(localMapping, hosts, componentsDictionary) : []),
    [isLoaded, localMapping, hosts, componentsDictionary],
  );

  const servicesMapping: ServiceMapping[] = useMemo(
    () => (isLoaded ? getServicesMapping(componentsMapping) : []),
    [isLoaded, componentsMapping],
  );

  const mappingValidation = useMemo(() => validate(componentsMapping, hosts.length), [componentsMapping, hosts.length]);

  const handleMapHostsToComponent = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmComponent) => {
      const newLocalMapping = mapHostsToComponent(servicesMapping, hosts, component);
      dispatch(setLocalMapping(newLocalMapping));
      setIsMappingChanged(true);
    },
    [dispatch, servicesMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newLocalMapping = localMapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      dispatch(setLocalMapping(newLocalMapping));
      setIsMappingChanged(true);
    },
    [dispatch, localMapping],
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

  const handleRevert = useCallback(() => {
    dispatch(setLocalMapping(originalMapping));
    setIsMappingChanged(false);
  }, [dispatch, originalMapping]);

  return {
    hostComponentMapping: localMapping,
    isLoading,
    isLoaded,
    hosts,
    hostsMapping,
    hostsMappingFilter,
    handleHostsMappingFilterChange,
    components,
    servicesMapping,
    servicesMappingFilter,
    handleServicesMappingFilterChange,
    isMappingChanged,
    mappingValidation,
    hasSaveError,
    handleMapHostsToComponent,
    handleUnmap,
    handleRevert,
  };
};
