import { useMemo } from 'react';
import HostContainerV2 from './HostContainer/HostContainerV2';
import type { HostMapping, MappingFilter, ComponentsMappingErrors } from '../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';
import s from './HostsMapping.module.scss';
import RestrictionsList from './RestrictionsList/RestrictionsList';

export interface HostsMappingV2Props {
  components: AdcmMappingComponent[];
  hostsMapping: HostMapping[];
  mappingErrors: ComponentsMappingErrors;
  mappingFilter: MappingFilter;
  relations: ComponentHostRelations;
  onMap: (components: AdcmMappingComponent[], host: AdcmHostShortView) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices: (component: AdcmMappingComponent) => void;
  isReadOnly?: boolean;
}

const HostsMappingV2 = ({
  components,
  hostsMapping,
  mappingErrors,
  mappingFilter,
  relations,
  onMap,
  onUnmap,
  onInstallServices,
  isReadOnly = false,
}: HostsMappingV2Props) => {
  const filteredHostsMapping = useMemo(() => {
    return hostsMapping.filter((hostMapping) =>
      hostMapping.host.name.toLowerCase().includes(mappingFilter.hostName.toLowerCase()),
    );
  }, [mappingFilter.hostName, hostsMapping]);

  return (
    <div className={s.hostsMapping}>
      <div data-test="mapping-container">
        {filteredHostsMapping.map((hostMapping) => (
          <HostContainerV2
            key={hostMapping.host.id}
            hostMapping={hostMapping}
            mappingErrors={mappingErrors}
            filter={mappingFilter}
            allComponents={components}
            className={s.hostContainer}
            onMap={onMap}
            onUnmap={onUnmap}
            isReadOnly={isReadOnly}
            relations={relations}
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

export default HostsMappingV2;
