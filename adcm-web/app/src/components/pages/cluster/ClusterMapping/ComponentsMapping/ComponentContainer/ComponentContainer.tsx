import { useState, useRef, useMemo } from 'react';
import { Tags } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappingItemTag from '../../MappingItemTag/MappingItemTag';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import MappingError from '../../MappingError/MappingError';
import { AdcmHostShortView, AdcmComponent } from '@models/adcm';
import { ComponentMapping, ServiceMappingFilter, ComponentMappingValidation } from '../../ClusterMapping.types';
import { getConstraintsLimit } from '../../ClusterMapping.utils';
import s from './ComponentContainer.module.scss';
import cn from 'classnames';
import { AdcmHostComponentMapRuleAction } from '@models/adcm/dynamicAction';

export interface ComponentContainerProps {
  componentMapping: ComponentMapping;
  componentMappingValidation: ComponentMappingValidation;
  filter: ServiceMappingFilter;
  allHosts: AdcmHostShortView[];
  onMap: (hosts: AdcmHostShortView[], component: AdcmComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  isDisabled?: boolean;
  allowActions?: AdcmHostComponentMapRuleAction[];
}

const defaultAllowActions = [AdcmHostComponentMapRuleAction.Add, AdcmHostComponentMapRuleAction.Remove];

const ComponentContainer = ({
  componentMapping,
  componentMappingValidation,
  filter,
  allHosts,
  onUnmap,
  onMap,
  isDisabled = false,
  allowActions = defaultAllowActions,
}: ComponentContainerProps) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const hostsOptions = useMemo(() => getOptionsFromArray(allHosts, (h) => h.name), [allHosts]);
  const { component, hosts } = componentMapping;

  const visibleHosts = useMemo(
    () => hosts.filter((host) => host.name.toLowerCase().includes(filter.hostName.toLowerCase())),
    [filter.hostName, hosts],
  );

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

  const isNotRequired = componentMappingValidation.isValid && hosts.length === 0;

  const containerClassName = cn(s.componentContainer, {
    [s.componentContainer_error]: !componentMappingValidation.isValid,
    [s.componentContainer_notRequired]: isNotRequired,
    [s.componentContainer_disabled]: isDisabled,
  });

  const titleClassName = cn(s.componentContainerHeader__title, {
    [s.componentContainerHeader__title_error]: !componentMappingValidation.isValid,
    [s.componentContainerHeader__title_notRequired]: isNotRequired,
  });

  const limit = getConstraintsLimit(component.constraints);

  if (visibleHosts.length === 0 && filter.isHideEmptyComponents) {
    return null;
  }

  return (
    <>
      <div className={containerClassName}>
        <div className={s.componentContainerHeader}>
          <span className={titleClassName}>{component.displayName}</span>
          <span className={s.componentContainerHeader__count}>
            {hosts.length} / {limit}
          </span>
          {!componentMappingValidation.isValid && !componentMappingValidation.constraintsValidationResult.isValid && (
            <MappingError message={componentMappingValidation.constraintsValidationResult.error} />
          )}
          <AddMappingButton
            className={s.componentContainerHeader__add}
            ref={addIconRef}
            label="Add hosts"
            onAddClick={handleAddClick}
            isDisabled={isDisabled || !allowActions.includes(AdcmHostComponentMapRuleAction.Add)}
          />
        </div>
        {visibleHosts.length > 0 && (
          <Tags className={s.componentContainer__hosts}>
            {visibleHosts.map((host) => (
              <MappingItemTag
                key={host.id}
                id={host.id}
                label={host.name}
                onDeleteClick={handleDelete}
                isDisabled={isDisabled || !allowActions.includes(AdcmHostComponentMapRuleAction.Remove)}
              />
            ))}
          </Tags>
        )}
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
