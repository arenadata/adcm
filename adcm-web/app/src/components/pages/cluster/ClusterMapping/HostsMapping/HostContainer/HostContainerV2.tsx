import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappedComponent from './MappedComponent/MappedComponent';
import type { ComponentsMappingErrors, HostMapping, MappingFilter } from '../../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent, ComponentId } from '@models/adcm';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';
import { buildHostContainerAvailabilityFromRelations } from '@utils/mapping/mappingContainerAvailability';
import s from './HostContainer.module.scss';
import cn from 'classnames';

export interface HostContainerV2Props {
  hostMapping: HostMapping;
  mappingErrors: ComponentsMappingErrors;
  filter: MappingFilter;
  allComponents: AdcmMappingComponent[];
  relations: ComponentHostRelations;
  className?: string;
  onMap: (components: AdcmMappingComponent[], host: AdcmHostShortView) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  isReadOnly?: boolean;
}

const HostContainerV2 = ({
  hostMapping,
  allComponents,
  mappingErrors,
  filter,
  className,
  relations,
  onMap,
  onUnmap,
  isReadOnly = false,
}: HostContainerV2Props) => {
  const { host, components } = hostMapping;
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);

  const mappedComponentIds = useMemo(() => new Set(components.map((component) => component.id)), [components]);

  const selectedComponentIds = useMemo(() => components.map((component) => component.id), [components]);

  const availability = useMemo(
    () => buildHostContainerAvailabilityFromRelations(relations, host.id, allComponents, mappedComponentIds),
    [relations, host.id, allComponents, mappedComponentIds],
  );

  const componentsOptions = useMemo<SelectOption<ComponentId>[]>(
    () =>
      allComponents
        .map((component) => {
          const option = availability.componentOptions[component.id];
          return {
            label: component.displayName,
            value: component.id,
            disabled: isReadOnly || Boolean(option?.disabled),
            title: option?.title,
          };
        })
        .sort((a, b) => Number(a.disabled) - Number(b.disabled)),

    [allComponents, availability.componentOptions, isReadOnly],
  );

  const visibleHostComponents = useMemo(
    () =>
      components.filter((component) =>
        component.displayName.toLowerCase().includes(filter.componentDisplayName.toLowerCase()),
      ),
    [components, filter.componentDisplayName],
  );

  if (visibleHostComponents.length === 0 && filter.isHideEmpty) {
    return null;
  }

  const hostClassName = cn(className, s.hostContainer, {
    [s.hostContainer_disabled]: isReadOnly || availability.addError,
  });

  const handleAddClick = () => {
    setIsSelectOpen(true);
  };

  const handleDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    const componentId = Number(e.currentTarget.dataset.id);
    onUnmap(host.id, componentId);
  };

  const handleMappingChange = (nextComponentIds: ComponentId[]) => {
    const selectedIds = new Set(nextComponentIds);
    onMap(
      allComponents.filter((component) => selectedIds.has(component.id)),
      host,
    );
  };

  return (
    <>
      <div className={hostClassName}>
        <div className={s.hostContainerHeader}>
          <span className={s.hostContainerHeader__title}>{host.name}</span>
          <span className={s.hostContainerHeader__count}>{components.length}</span>
          <AddMappingButton
            className={s.hostContainerHeader__add}
            ref={addIconRef}
            label="Add components"
            onClick={handleAddClick}
            tooltip={availability.addError}
            isDisabled={isReadOnly || Boolean(availability.addError)}
          />
        </div>
        {visibleHostComponents.length > 0 && (
          <Tags className={s.hostContainer__components}>
            {visibleHostComponents.map((component) => {
              const deleteState = availability.mappedComponentDelete[component.id];
              return (
                <MappedComponent
                  key={component.id}
                  id={component.id}
                  label={component.displayName}
                  mappingErrors={mappingErrors[component.id]}
                  onDeleteClick={handleDelete}
                  deleteButtonTooltip={deleteState?.title}
                  isDisabled={isReadOnly || Boolean(deleteState?.disabled)}
                />
              );
            })}
          </Tags>
        )}
      </div>
      <MappingItemSelect
        isOpen={isSelectOpen}
        checkAllLabel="All components"
        searchPlaceholder="Search component"
        options={componentsOptions}
        value={selectedComponentIds}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default HostContainerV2;
