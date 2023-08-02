import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import { getMappings, saveMapping, cleanupMappings } from '@store/adcm/cluster/mapping/mappingSlice';
import { AdcmComponent, AdcmHostShortView, AdcmMapping } from '@models/adcm';
import { arrayToHash } from '@utils/arrayUtils';
import { getHostsMapping, getServicesMapping, mapComponentsToHost, mapHostsToComponent } from './ClusterMapping.utils';
import { HostMappingFilter, HostMapping, ServiceMappingFilter, ServiceMapping } from './ClusterMapping.types';

export const useClusterMapping = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const {
    hosts,
    components,
    mapping: originalMapping,
    isLoaded,
    hasSaveError,
  } = useStore(({ adcm }) => adcm.clusterMapping);

  const [localMapping, setLocalMapping] = useState<AdcmMapping[]>([]);
  const [isMappingChanged, setIsMappingChanged] = useState(false);

  const hostsDictionary = useMemo(() => arrayToHash(hosts, (h) => h.id), [hosts]);
  const componentsDictionary = useMemo(() => arrayToHash(components, (c) => c.id), [components]);

  const [hostsMappingFilter, setHostsMappingFilter] = useState<HostMappingFilter>({ componentDisplayName: '' });
  const [servicesMappingFilter, setServicesMappingFilter] = useState<ServiceMappingFilter>({ hostName: '' });

  useEffect(() => {
    if (!isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
    }

    return () => {
      dispatch(cleanupMappings());
    };
  }, [clusterId, dispatch]);

  useEffect(() => {
    setLocalMapping(originalMapping);
  }, [originalMapping]);

  const hostsMapping: HostMapping[] = useMemo(
    () => (isLoaded ? getHostsMapping(hosts, localMapping, componentsDictionary, hostsMappingFilter) : []),
    [isLoaded, hosts, localMapping, componentsDictionary, hostsMappingFilter],
  );

  const servicesMapping: ServiceMapping[] = useMemo(
    () => (isLoaded ? getServicesMapping(components, localMapping, hostsDictionary, servicesMappingFilter) : []),
    [isLoaded, components, localMapping, hostsDictionary, servicesMappingFilter],
  );

  const isValid = useMemo(() => servicesMapping.every((m) => m.validationSummary === 'valid'), [servicesMapping]);

  const handleMapHostsToComponent = useCallback(
    (hosts: AdcmHostShortView[], component: AdcmComponent) => {
      const newLocalMapping = mapHostsToComponent(servicesMapping, hosts, component);
      setLocalMapping(newLocalMapping);
      setIsMappingChanged(true);
    },
    [servicesMapping],
  );

  const handleMapComponentsToHost = useCallback(
    (components: AdcmComponent[], host: AdcmHostShortView) => {
      const newMapping = mapComponentsToHost(hostsMapping, components, host);
      setLocalMapping(newMapping);
      setIsMappingChanged(true);
    },
    [hostsMapping],
  );

  const handleUnmap = useCallback(
    (hostId: number, componentId: number) => {
      const newLocalMapping = localMapping.filter((m) => !(m.hostId === hostId && m.componentId === componentId));
      setLocalMapping(newLocalMapping);
      setIsMappingChanged(true);
    },
    [localMapping],
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
    setLocalMapping(originalMapping);
    setIsMappingChanged(false);
  }, [originalMapping]);

  const handleSave = useCallback(() => {
    dispatch(saveMapping({ clusterId, mapping: localMapping }));
  }, [dispatch, clusterId, localMapping]);

  return {
    hosts,
    hostsMapping,
    hostsMappingFilter,
    handleHostsMappingFilterChange,
    components,
    servicesMapping,
    servicesMappingFilter,
    handleServicesMappingFilterChange,
    isMappingChanged,
    isValid,
    hasSaveError,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    handleRevert,
    handleSave,
  };
};
