import { useClusterMapping } from '../useClusterMapping';
import HostContainer from './HostContainer/HostContainer';
import ClusterMappingToolbar from '../ClusterMappingToolbar/ClusterMappingToolbar';
import s from './HostsMapping.module.scss';

const HostsMapping = () => {
  const {
    components,
    hostsMapping,
    hostsMappingFilter,
    handleHostsMappingFilterChange,
    isMappingChanged,
    isValid,
    hasSaveError,
    handleMapComponentsToHost,
    handleUnmap,
    handleSave,
    handleRevert,
  } = useClusterMapping();

  const handleFilterChange = (componentDisplayName: string) => {
    handleHostsMappingFilterChange({ componentDisplayName });
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
