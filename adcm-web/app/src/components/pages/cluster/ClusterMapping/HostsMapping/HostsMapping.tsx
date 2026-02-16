import { useMemo } from 'react';
import HostContainer from './HostContainer/HostContainer';
import type {
  HostMapping,
  MappingFilter,
  ComponentsMappingErrors,
  ComponentAvailabilityErrors,
} from '../ClusterMapping.types';
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
  isReadOnly?: boolean;
  checkComponentMappingAvailability: (component: AdcmMappingComponent) => ComponentAvailabilityErrors;
  checkHostMappingAvailability: (host: AdcmHostShortView, component?: AdcmMappingComponent) => string | undefined;
  checkHostUnmappingAvailability: (host: AdcmHostShortView, component?: AdcmMappingComponent) => string | undefined;
}

const HostsMapping = ({
  components,
  hostsMapping,
  mappingErrors,
  mappingFilter,
  onMap,
  onUnmap,
  onInstallServices,
  isReadOnly = false,
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
}: HostsMappingProps) => {
  const filteredHostsMapping = useMemo(() => {
    return hostsMapping.filter((hostMapping) =>
      hostMapping.host.name.toLowerCase().includes(mappingFilter.hostName.toLowerCase()),
    );
  }, [mappingFilter.hostName, hostsMapping]);

  return (
    <div className={s.hostsMapping}>
      <div data-test="mapping-container">
        {filteredHostsMapping.map((hostMapping) => {
          const checkHostAvailability = (host: AdcmHostShortView) => {
            if (hostMapping.components.length === 0) {
              return checkHostMappingAvailability(host);
            }
            return checkHostUnmappingAvailability(host);
          };

          const checkComponentAddingAvailability = (component: AdcmMappingComponent) => {
            const { componentNotAvailableError } = checkComponentMappingAvailability(component);
            return componentNotAvailableError ?? checkHostMappingAvailability(hostMapping.host, component);
          };

          const checkComponentRemovingAvailability = (component: AdcmMappingComponent) => {
            const { componentNotAvailableError } = checkComponentMappingAvailability(component);
            return componentNotAvailableError ?? checkHostUnmappingAvailability(hostMapping.host, component);
          };
          return (
            <HostContainer
              key={hostMapping.host.id}
              hostMapping={hostMapping}
              mappingErrors={mappingErrors}
              filter={mappingFilter}
              allComponents={components}
              className={s.hostContainer}
              onMap={onMap}
              onUnmap={onUnmap}
              isReadOnly={isReadOnly}
              checkHostAvailability={checkHostAvailability}
              checkComponentMappingAvailability={checkComponentAddingAvailability}
              checkComponentUnmappingAvailability={checkComponentRemovingAvailability}
            />
          );
        })}
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
