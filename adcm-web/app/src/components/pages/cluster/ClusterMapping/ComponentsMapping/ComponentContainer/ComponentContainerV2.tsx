import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappedHost from './MappedHost/MappedHost';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import ComponentRestrictions from '../../HostsMapping/RestrictionsList/ComponentRestrictions';
import type { AdcmHostShortView, AdcmMappingComponent, HostId } from '@models/adcm';
import type { ComponentMapping, ComponentMappingErrors, MappingFilter } from '../../ClusterMapping.types';
import { getConstraintsLimit } from '../../ClusterMapping.utils';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';
import { buildComponentContainerAvailabilityFromRelations } from '@utils/mapping/mappingContainerAvailability';
import s from './ComponentContainer.module.scss';
import cn from 'classnames';

export interface ComponentContainerV2Props {
  componentMapping: ComponentMapping;
  mappingErrors?: ComponentMappingErrors;
  filter: MappingFilter;
  allHosts: AdcmHostShortView[];
  relations: ComponentHostRelations;
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  onInstallServices?: (component: AdcmMappingComponent) => void;
  isReadOnly?: boolean;
}

const ComponentContainerV2 = ({
  componentMapping,
  mappingErrors,
  filter,
  allHosts,
  relations,
  onUnmap,
  onMap,
  onInstallServices,
  isReadOnly = false,
}: ComponentContainerV2Props) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const { component, hosts } = componentMapping;

  const mappedHostIds = useMemo(() => new Set(hosts.map((host) => host.id)), [hosts]);

  const selectedHostIds = useMemo(() => hosts.map((host) => host.id), [hosts]);

  const availability = useMemo(
    () => buildComponentContainerAvailabilityFromRelations(relations, component.id, allHosts, mappedHostIds),
    [relations, component.id, allHosts, mappedHostIds],
  );

  const hostsOptions = useMemo<SelectOption<HostId>[]>(
    () =>
      allHosts
        .map((host) => {
          const option = availability.hostOptions[host.id];
          return {
            label: host.name,
            value: host.id,
            disabled: isReadOnly || Boolean(option?.disabled),
            title: option?.title,
          };
        })
        .sort((a, b) => Number(a.disabled) - Number(b.disabled)),

    [allHosts, availability.hostOptions, isReadOnly],
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

  const handleMappingChange = (nextHostIds: HostId[]) => {
    const selectedIds = new Set(nextHostIds);
    onMap(
      allHosts.filter((host) => selectedIds.has(host.id)),
      component,
    );
  };

  const handleInstallServices = () => {
    onInstallServices?.(component);
  };

  const isMappingValid = mappingErrors === undefined;
  const isNotRequired = isMappingValid && hosts.length === 0;
  const isOptional = component.constraints[0] === 0 && hosts.length === 0 && !availability.notAvailableError;

  const containerClassName = cn(s.componentContainer, {
    [s.componentContainer_valid]: hosts.length > 0 && isMappingValid,
    [s.componentContainer_optional]: isOptional,
    [s.componentContainer_disabled]: isReadOnly || availability.notAvailableError,
    [s.componentContainer_notRequired]: isNotRequired,
    [s.componentContainer_error]: !isMappingValid,
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
            tooltip={availability.addError}
            isDisabled={isReadOnly || Boolean(availability.addError)}
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
                  const deleteState = availability.mappedHostDelete[host.id];
                  return (
                    <MappedHost
                      key={host.id}
                      id={host.id}
                      label={host.name}
                      onDeleteClick={handleDelete}
                      deleteButtonTooltip={deleteState?.title}
                      isDisabled={isReadOnly || Boolean(deleteState?.disabled)}
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
        value={selectedHostIds}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default ComponentContainerV2;
