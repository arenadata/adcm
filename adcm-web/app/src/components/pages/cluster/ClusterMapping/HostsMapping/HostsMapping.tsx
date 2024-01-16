import { useClusterMapping } from '../useClusterMapping';
import HostContainer from './HostContainer/HostContainer';
import ClusterMappingToolbar from '../ClusterMappingToolbar/ClusterMappingToolbar';
import s from './HostsMapping.module.scss';
import { SearchInput, Switch } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const HostsMapping = () => {
  const dispatch = useDispatch();

  const { hosts, components, localMapping, isLoaded } = useStore(({ adcm }) => adcm.clusterMapping);
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const { hostsMapping, hostsMappingFilter, handleHostsMappingFilterChange, mappingValidation } = useClusterMapping(
    localMapping,
    hosts,
    components,
    notAddedServicesDictionary,
    isLoaded,
  );

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleHostsMappingFilterChange({ componentDisplayName: event.target.value });
  };

  const handleHideEmptyHostsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleHostsMappingFilterChange({ isHideEmptyHosts: event.target.checked });
  };

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);
  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Mapping' },
          { label: 'Hosts view' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div className={s.hostsMapping}>
      <ClusterMappingToolbar className={s.hostsMapping__toolbar}>
        <SearchInput
          placeholder="Search components"
          value={hostsMappingFilter.componentDisplayName}
          onChange={handleFilterChange}
        />
        <Switch
          isToggled={hostsMappingFilter.isHideEmptyHosts}
          onChange={handleHideEmptyHostsChange}
          label="Hide empty hosts"
        />
      </ClusterMappingToolbar>
      <div className={s.hostsMapping__content}>
        <div>
          {hostsMapping.map((hostMapping) => (
            <HostContainer
              key={hostMapping.host.id}
              hostMapping={hostMapping}
              mappingValidation={mappingValidation}
              filter={hostsMappingFilter}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default HostsMapping;
