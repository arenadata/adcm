import { useMemo, useRef, useState } from 'react';
import type { SelectOption } from '@uikit';
import { Tags } from '@uikit';
import MappedComponent from './MappedComponent/MappedComponent';
import type { ComponentsMappingErrors, HostMapping, MappingFilter } from '../../ClusterMapping.types';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
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
  isReadOnly?: boolean;
  checkHostAvailability: (host: AdcmHostShortView) => string | undefined;
  checkComponentMappingAvailability: (component: AdcmMappingComponent) => string | undefined;
  checkComponentUnmappingAvailability: (component: AdcmMappingComponent) => string | undefined;
}

const HostContainer = ({
  hostMapping,
  allComponents,
  mappingErrors,
  filter,
  className,
  checkHostAvailability,
  checkComponentMappingAvailability,
  checkComponentUnmappingAvailability,
  onMap,
  onUnmap,
  isReadOnly = false,
}: HostContainerProps) => {
  const { host, components } = hostMapping;
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);

  const componentsSets = useMemo(() => new Set(components.map((c) => c.id)), [components]);

  const componentsErrors = useMemo(() => {
    const result: { [componentId: number]: { allowMapError?: string; allowUnmapError?: string } } = {};

    for (const component of allComponents) {
      result[component.id] = {
        allowMapError: checkComponentMappingAvailability(component),
        allowUnmapError: checkComponentUnmappingAvailability(component),
      };
    }

    return result;
  }, [allComponents, host]);

  const hostNotAvailableError = checkHostAvailability(host);

  const componentsOptions = useMemo<SelectOption<AdcmMappingComponent>[]>(
    () =>
      allComponents
        .map((component) => {
          const isEnabled = Boolean(
            (componentsErrors[component.id].allowMapError === undefined && !componentsSets.has(component.id)) ||
              (componentsErrors[component.id].allowUnmapError === undefined && componentsSets.has(component.id)),
          );

          const title = !isEnabled
            ? (componentsErrors[component.id].allowMapError ?? componentsErrors[component.id].allowUnmapError)
            : undefined;

          return {
            label: component.displayName,
            value: component,
            disabled: isReadOnly || !isEnabled,
            title,
          };
        })
        .sort((a, b) => (a.disabled === b.disabled ? 0 : a.disabled ? 1 : -1)),
    [allComponents, componentsErrors],
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
    [s.hostContainer_disabled]: isReadOnly || hostNotAvailableError,
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
            isDisabled={isReadOnly || Boolean(hostNotAvailableError)}
          />
        </div>
        {visibleHostComponents.length > 0 && (
          <Tags className={s.hostContainer__components}>
            {visibleHostComponents.map((component) => {
              const error = componentsErrors[component.id].allowUnmapError;
              return (
                <MappedComponent
                  key={component.id}
                  id={component.id}
                  label={component.displayName}
                  mappingErrors={mappingErrors[component.id]}
                  onDeleteClick={handleDelete}
                  deleteButtonTooltip={error}
                  isDisabled={isReadOnly || Boolean(error)}
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
