import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappedHost from './MappedHost/MappedHost';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import ComponentRestrictions from '../../HostsMapping/RestrictionsList/ComponentRestrictions';
import { type AdcmHostShortView, type AdcmMappingComponent } from '@models/adcm';
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
  denyAddHostReason?: React.ReactNode;
  denyRemoveHostReason?: React.ReactNode;
  checkComponentMappingAvailability: (component: AdcmMappingComponent) => ComponentAvailabilityErrors;
  checkHostMappingAvailability: (host: AdcmHostShortView) => string | undefined;
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
}: ComponentContainerProps) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const { component, hosts } = componentMapping;
  const { componentNotAvailableError, addingHostsNotAllowedError } = checkComponentMappingAvailability(component);

  const hostsOptions = useMemo<SelectOption<AdcmHostShortView>[]>(
    () =>
      allHosts.map((host) => {
        const hostMappingAvailabilityError = checkHostMappingAvailability(host);
        return {
          label: host.name,
          value: host,
          disabled: Boolean(hostMappingAvailabilityError),
          title: hostMappingAvailabilityError,
        };
      }),
    [allHosts, checkHostMappingAvailability],
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
            tooltip={componentNotAvailableError ?? addingHostsNotAllowedError}
            isDisabled={Boolean(componentNotAvailableError ?? addingHostsNotAllowedError)}
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
                  const removingHostNotAllowedError = checkHostMappingAvailability(host);
                  return (
                    <MappedHost
                      key={host.id}
                      id={host.id}
                      label={host.name}
                      onDeleteClick={handleDelete}
                      deleteButtonTooltip={componentNotAvailableError ?? removingHostNotAllowedError}
                      isDisabled={Boolean(componentNotAvailableError ?? removingHostNotAllowedError)}
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
