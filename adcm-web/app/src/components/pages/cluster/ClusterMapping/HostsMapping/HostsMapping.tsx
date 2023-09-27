import { useClusterMapping } from '../useClusterMapping';
import HostContainer from './HostContainer/HostContainer';
import ClusterMappingToolbar from '../ClusterMappingToolbar/ClusterMappingToolbar';
import s from './HostsMapping.module.scss';
import { SearchInput, Switch } from '@uikit';

const HostsMapping = () => {
  const { hostsMapping, hostsMappingFilter, handleHostsMappingFilterChange, mappingValidation } = useClusterMapping();

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleHostsMappingFilterChange({ componentDisplayName: event.target.value });
  };

  const handleHideEmptyHostsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleHostsMappingFilterChange({ isHideEmptyHosts: event.target.checked });
  };

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
