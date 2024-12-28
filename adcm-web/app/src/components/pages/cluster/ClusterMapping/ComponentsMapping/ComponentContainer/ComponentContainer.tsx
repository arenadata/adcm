import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappedHost from './MappedHost/MappedHost';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import ComponentRestrictions from '../../HostsMapping/RestrictionsList/ComponentRestrictions';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import type {
  ComponentAvailabilityErrors,
  ComponentMapping,
  ComponentMappingErrors,
  MappingFilter,
} from '../../ClusterMapping.types';
import { getConstraintsLimit } from '../../ClusterMapping.utils';
import s from './ComponentContainer.module.scss';
import cn from 'classnames';

export interface ComponentContainerProps {
  componentMapping: ComponentMapping;
  mappingErrors?: ComponentMappingErrors;
  filter: MappingFilter;
  allHosts: AdcmHostShortView[];
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices?: (component: AdcmMappingComponent) => void;
  checkComponentMappingAvailability: (component: AdcmMappingComponent) => ComponentAvailabilityErrors;
  checkHostMappingAvailability: (host: AdcmHostShortView) => string | undefined;
  checkHostUnmappingAvailability: (host: AdcmHostShortView) => string | undefined;
}

const ComponentContainer = ({
  componentMapping,
  mappingErrors,
  filter,
  allHosts,
  onUnmap,
  onMap,
  onInstallServices,
  checkComponentMappingAvailability,
  checkHostMappingAvailability,
  checkHostUnmappingAvailability,
}: ComponentContainerProps) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const { component, hosts } = componentMapping;
  const { componentNotAvailableError, addingHostsNotAllowedError, removingHostsNotAllowedError } =
    checkComponentMappingAvailability(component);

  const hostsSets = useMemo(() => new Set(hosts.map((h) => h.id)), [hosts]);

  const componentMapError = componentNotAvailableError ?? addingHostsNotAllowedError;
  const componentUnmapError = componentNotAvailableError ?? removingHostsNotAllowedError;

  const hostsErrors = useMemo(() => {
    const result: { [hostId: number]: { allowMapError?: string; allowUnmapError?: string } } = {};

    for (const host of allHosts) {
      result[host.id] = {
        allowMapError: componentMapError ?? checkHostMappingAvailability(host),
        allowUnmapError: componentUnmapError ?? checkHostUnmappingAvailability(host),
      };
    }

    return result;
  }, [allHosts, componentMapping]);

  const hostsOptions = useMemo<SelectOption<AdcmHostShortView>[]>(
    () =>
      allHosts.map((host) => {
        const isEnabled = Boolean(
          (hostsErrors[host.id].allowMapError === undefined && !hostsSets.has(host.id)) ||
            (hostsErrors[host.id].allowUnmapError === undefined && hostsSets.has(host.id)),
        );

        return {
          label: host.name,
          value: host,
          disabled: !isEnabled,
          title: hostsErrors[host.id].allowMapError ?? hostsErrors[host.id].allowUnmapError,
        };
      }),
    [allHosts, hostsErrors],
  );

  const visibleHosts = useMemo(
    () => hosts.filter((host) => host.name.toLowerCase().includes(filter.hostName.toLowerCase())),
    [filter.hostName, hosts],
  );

  if (visibleHosts.length === 0 && filter.isHideEmpty) {
    return null;
  }

  const handleAddClick = () => {
    setIsSelectOpen(true);
  };

  const handleDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    const hostId = Number(e.currentTarget.dataset.id);
    onUnmap(hostId, component.id);
  };

  const handleMappingChange = (hosts: AdcmHostShortView[]) => {
    onMap(hosts, component);
  };

  const handleInstallServices = () => {
    onInstallServices?.(component);
  };

  const isMappingValid = mappingErrors === undefined;
  const isNotRequired = isMappingValid && hosts.length === 0;

  const containerClassName = cn(s.componentContainer, {
    [s.componentContainer_error]: !isMappingValid,
    [s.componentContainer_notRequired]: isNotRequired,
    [s.componentContainer_disabled]: componentNotAvailableError,
  });

  const titleClassName = cn(s.componentContainerHeader__title, {
    [s.componentContainerHeader__title_error]: !isMappingValid,
    [s.componentContainerHeader__title_notRequired]: isNotRequired,
  });

  const limit = getConstraintsLimit(component.constraints);

  return (
    <>
      <div className={containerClassName}>
        <div className={s.componentContainerHeader}>
          <span className={titleClassName}>{component.displayName}</span>
          <span className={s.componentContainerHeader__count}>
            {hosts.length} / {limit}
          </span>
          <AddMappingButton
            className={s.componentContainerHeader__add}
            ref={addIconRef}
            label="Add hosts"
            onClick={handleAddClick}
            tooltip={componentMapError}
            isDisabled={Boolean(componentMapError)}
          />
        </div>
        <div className={s.componentContainerContent}>
          {mappingErrors && (
            <div className={s.componentContainerContent__restrictions}>
              <span className={s.componentContainerContent__restrictionsTitle}>Constraints:</span>
              <ComponentRestrictions
                onInstallServices={handleInstallServices}
                key={component.id}
                errors={mappingErrors}
              />
            </div>
          )}
          {visibleHosts.length > 0 && (
            <div className={s.componentContainerContent__mappedHosts}>
              <Tags>
                {visibleHosts.map((host) => {
                  const error = hostsErrors[host.id].allowUnmapError;
                  return (
                    <MappedHost
                      key={host.id}
                      id={host.id}
                      label={host.name}
                      onDeleteClick={handleDelete}
                      deleteButtonTooltip={error}
                      isDisabled={Boolean(error)}
                    />
                  );
                })}
              </Tags>
            </div>
          )}
        </div>
      </div>
      <MappingItemSelect
        isOpen={isSelectOpen}
        checkAllLabel="All hosts"
        searchPlaceholder="Search host"
        options={hostsOptions}
        value={hosts}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default ComponentContainer;
