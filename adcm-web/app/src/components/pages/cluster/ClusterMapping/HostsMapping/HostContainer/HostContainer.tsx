import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappedComponent from './MappedComponent/MappedComponent';
import type { ComponentsMappingErrors, HostMapping, MappingFilter } from '../../ClusterMapping.types';
import { type AdcmHostShortView, type AdcmMappingComponent } from '@models/adcm';
import { checkHostMappingAvailability, checkComponentMappingAvailability } from '../../ClusterMapping.utils';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import s from './HostContainer.module.scss';
import cn from 'classnames';

export interface HostContainerProps {
  hostMapping: HostMapping;
  mappingErrors: ComponentsMappingErrors;
  filter: MappingFilter;
  allComponents: AdcmMappingComponent[];
  className?: string;
  onMap: (components: AdcmMappingComponent[], host: AdcmHostShortView) => void;
  onUnmap: (hostId: number, componentId: number) => void;
}

const HostContainer = ({
  hostMapping,
  allComponents,
  mappingErrors,
  filter,
  className,
  onMap,
  onUnmap,
}: HostContainerProps) => {
  const { host, components } = hostMapping;
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);

  const hostNotAvailableError = checkHostMappingAvailability(host);

  const componentsOptions = useMemo<SelectOption<AdcmMappingComponent>[]>(
    () =>
      allComponents.map((component) => {
        const { componentNotAvailableError } = checkComponentMappingAvailability(component);
        return {
          label: component.displayName,
          value: component,
          disabled: Boolean(componentNotAvailableError),
          title: componentNotAvailableError,
        };
      }),
    [allComponents],
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
    [s.hostContainer_disabled]: hostNotAvailableError,
  });

  const handleAddClick = () => {
    setIsSelectOpen(true);
  };

  const handleDelete = (e: React.MouseEvent<HTMLButtonElement>) => {
    const componentId = Number(e.currentTarget.dataset.id);
    onUnmap(host.id, componentId);
  };

  const handleMappingChange = (components: AdcmMappingComponent[]) => {
    onMap(components, host);
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
            tooltip={hostNotAvailableError}
            isDisabled={Boolean(hostNotAvailableError)}
          />
        </div>
        {visibleHostComponents.length > 0 && (
          <Tags className={s.hostContainer__components}>
            {visibleHostComponents.map((component) => {
              const { componentNotAvailableError } = checkComponentMappingAvailability(component);
              return (
                <MappedComponent
                  key={component.id}
                  id={component.id}
                  label={component.displayName}
                  mappingErrors={mappingErrors[component.id]}
                  onDeleteClick={handleDelete}
                  deleteButtonTooltip={hostNotAvailableError ?? componentNotAvailableError}
                  isDisabled={Boolean(hostNotAvailableError ?? componentNotAvailableError)}
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
        value={components}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default HostContainer;
