import { useClusterMapping } from '../useClusterMapping';
import HostContainer from './HostContainer/HostContainer';
import ClusterMappingToolbar from '../ClusterMappingToolbar/ClusterMappingToolbar';
import s from './HostsMapping.module.scss';
import { useParams } from 'react-router-dom';
import { saveMapping } from '@store/adcm/cluster/mapping/mappingSlice';
import { useDispatch } from '@hooks';

const HostsMapping = () => {
  const dispatch = useDispatch();

  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const {
    hostComponentMapping,
    components,
    hostsMapping,
    hostsMappingFilter,
    handleHostsMappingFilterChange,
    isMappingChanged,
    isValid,
    hasSaveError,
    handleMapComponentsToHost,
    handleUnmap,
    handleRevert,
  } = useClusterMapping(clusterId);

  const handleFilterChange = (componentDisplayName: string) => {
    handleHostsMappingFilterChange({ componentDisplayName });
  };

  const handleSave = () => {
    dispatch(saveMapping({ clusterId, mapping: hostComponentMapping }));
  };

  return (
    <div className={s.hostsMapping}>
      <ClusterMappingToolbar
        className={s.hostsMapping__toolbar}
        filter={hostsMappingFilter.componentDisplayName}
        filterPlaceHolder="Search components"
        hasError={hasSaveError}
        isSaveDisabled={!isMappingChanged || !isValid}
        onSave={handleSave}
        onFilterChange={handleFilterChange}
        onRevert={handleRevert}
      />
      <div className={s.hostsMapping__content}>
        <div>
          {hostsMapping.map((hostMapping) => (
            <HostContainer
              key={hostMapping.host.id}
              hostMapping={hostMapping}
              allComponents={components}
              onMap={handleMapComponentsToHost}
              onUnmap={handleUnmap}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

export default HostsMapping;
