import { useMemo } from 'react';
import HostContainer from './HostContainer/HostContainer';
import type { HostMapping, MappingFilter, ComponentsMappingErrors } from '../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import s from './HostsMapping.module.scss';
import RestrictionsList from './RestrictionsList/RestrictionsList';

export interface HostsMappingProps {
  components: AdcmMappingComponent[];
  hostsMapping: HostMapping[];
  mappingErrors: ComponentsMappingErrors;
  mappingFilter: MappingFilter;
  onMap: (components: AdcmMappingComponent[], host: AdcmHostShortView) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices: (component: AdcmMappingComponent) => void;
}

const HostsMapping = ({
  components,
  hostsMapping,
  mappingErrors,
  mappingFilter,
  onMap,
  onUnmap,
  onInstallServices,
}: HostsMappingProps) => {
  const filteredHostsMapping = useMemo(() => {
    return hostsMapping.filter((hostMapping) =>
      hostMapping.host.name.toLowerCase().includes(mappingFilter.hostName.toLowerCase()),
    );
  }, [mappingFilter.hostName, hostsMapping]);

  return (
    <div className={s.hostsMapping}>
      <div data-test="mapping-container">
        {filteredHostsMapping.map((hostMapping) => (
          <HostContainer
            key={hostMapping.host.id}
            hostMapping={hostMapping}
            mappingErrors={mappingErrors}
            filter={mappingFilter}
            allComponents={components}
            className={s.hostContainer}
            onMap={onMap}
            onUnmap={onUnmap}
          />
        ))}
      </div>
      <RestrictionsList
        allComponents={components}
        mappingErrors={mappingErrors}
        onInstallServices={onInstallServices}
      />
    </div>
  );
};

export default HostsMapping;
