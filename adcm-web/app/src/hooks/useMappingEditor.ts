import { useCallback, useEffect, useMemo, useState } from 'react';
import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import type { MappingFilter } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { mapComponentsToHost, mapHostsToComponent } from '@pages/cluster/ClusterMapping/ClusterMapping.utils';
import type { SortDirection } from '@models/table';
import { buildMappingCore } from '@utils/mapping/buildMappingViewModel';
import { buildComponentHostRelations } from '@utils/mapping/componentHostRelations';
import { layoutMappingViewModel } from '@utils/mapping/mappingLayout';
import type { MappingViewConfig } from '@utils/mapping/mapping.types';

export const useMappingEditor = (
  baselineMapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
  viewConfig: MappingViewConfig,
) => {
  const [localMapping, setLocalMapping] = useState<AdcmMapping[]>(baselineMapping);
  const [isMappingChanged, setIsMappingChanged] = useState(false);
  const [mappingFilter, setMappingFilter] = useState<MappingFilter>({
    componentDisplayName: '',
    hostName: '',
    isHideEmpty: false,
  });
  const [mappingSortDirection, setMappingSortDirection] = useState<SortDirection>(viewConfig.sortDirection ?? 'asc');

  useEffect(() => {
    if (isLoaded) {
      setLocalMapping(baselineMapping);
      setIsMappingChanged(false);
    }
  }, [isLoaded, baselineMapping]);

  const relations = useMemo(() => {
    if (!isLoaded) {
      return undefined;
    }
    return buildComponentHostRelations({
      hosts,
      components,
      baselinePairs: baselineMapping,
      policy: viewConfig.strategy,
    });
  }, [isLoaded, hosts, components, baselineMapping, viewConfig.strategy]);

  const mappingCore = useMemo(() => {
    if (!isLoaded || !relations) {
      return null;
    }
    return buildMappingCore(localMapping, hosts, components, notAddedServicesDictionary, relations);
  }, [isLoaded, localMapping, hosts, components, notAddedServicesDictionary, relations]);

  const viewModel = useMemo(() => {
    if (!mappingCore) {
      return undefined;
    }
    return layoutMappingViewModel(mappingCore.model, mappingCore.availability, {
      kind: viewConfig.kind,
      sort: viewConfig.sort,
      sortDirection: mappingSortDirection,
    });
  }, [mappingCore, viewConfig.kind, viewConfig.sort, mappingSortDirection]);

  const handleMapHostsToComponent = useCallback((nextHosts: AdcmHostShortView[], component: AdcmMappingComponent) => {
    setLocalMapping((prevMapping) => mapHostsToComponent(prevMapping, nextHosts, component));
    setIsMappingChanged(true);
  }, []);

  const handleMapComponentsToHost = useCallback((nextComponents: AdcmMappingComponent[], host: AdcmHostShortView) => {
    setLocalMapping((prevMapping) => mapComponentsToHost(prevMapping, nextComponents, host));
    setIsMappingChanged(true);
  }, []);

  const handleUnmap = useCallback((hostId: number, componentId: number) => {
    setLocalMapping((prevMapping) =>
      prevMapping.filter((pair) => !(pair.hostId === hostId && pair.componentId === componentId)),
    );
    setIsMappingChanged(true);
  }, []);

  const handleMappingFilterChange = (changes: Partial<MappingFilter>) => {
    setMappingFilter((prevFilter) => ({ ...prevFilter, ...changes }));
  };

  const handleReset = () => {
    setLocalMapping(baselineMapping);
    setIsMappingChanged(false);
  };

  return {
    hosts,
    components,
    localMapping,
    isMappingChanged,
    mappingFilter,
    handleMappingFilterChange,
    mappingSortDirection,
    handleMappingSortDirectionChange: setMappingSortDirection,
    viewModel,
    mappingErrors: mappingCore?.mappingErrors ?? {},
    servicesMapping: mappingCore?.model.servicesMapping ?? [],
    hostsMapping: mappingCore?.model.hostsMapping ?? [],
    unmappedHostsId: mappingCore?.model.unmappedHostsId ?? [],
    availability: mappingCore?.availability,
    handleMapHostsToComponent,
    handleMapComponentsToHost,
    handleUnmap,
    handleReset,
    relations,
  };
};
