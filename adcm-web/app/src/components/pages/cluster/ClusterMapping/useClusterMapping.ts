import { useCallback, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { setLocalMapping, revertChanges } from '@store/adcm/cluster/mapping/mappingSlice';
import { AdcmMappingComponent, AdcmHostShortView } from '@models/adcm';
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

  const { hosts, components, localMapping, isLoaded, isLoading, hasSaveError, state } = useStore(
    ({ adcm }) => adcm.clusterMapping,
  );
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

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

  const servicesMappingDictionary = useMemo(() => {
    return Object.fromEntries(servicesMapping.map((item) => [item.service.prototype.id, item]));
  }, [servicesMapping]);

  const mappingValidation = useMemo(() => {
    return validate(componentsMapping, {
      servicesMappingDictionary,
      notAddedServicesDictionary,
      allHostsCount: hosts.length,
    });
  }, [componentsMapping, servicesMappingDictionary, notAddedServicesDictionary, hosts.length]);

  const handleMapHostsToComponent = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => {
      const newLocalMapping = mapHostsToComponent(servicesMapping, hosts, component);
      dispatch(setLocalMapping(newLocalMapping));
    },
    [dispatch, servicesMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newLocalMapping = localMapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      dispatch(setLocalMapping(newLocalMapping));
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
    dispatch(revertChanges());
  }, [dispatch]);

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
    mappingState: state,
    mappingValidation,
    hasSaveError,
    handleMapHostsToComponent,
    handleUnmap,
    handleRevert,
  };
};
