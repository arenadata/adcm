import { useMemo, useRef, useState } from 'react';
import { SelectOption, Tags } from '@uikit';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappingItemTag from '../../MappingItemTag/MappingItemTag';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import MappingError from '../../MappingError/MappingError';
import {
  AdcmHostComponentMapRuleAction,
  AdcmHostShortView,
  AdcmMaintenanceMode,
  AdcmMappingComponent,
} from '@models/adcm';
import { ComponentMapping, ComponentMappingValidation, ServiceMappingFilter } from '../../ClusterMapping.types';
import { getConstraintsLimit, isComponentDependOnNotAddedServices } from '../../ClusterMapping.utils';
import s from './ComponentContainer.module.scss';
import cn from 'classnames';
import { useDispatch, useStore } from '@hooks';
import { openRequiredServicesDialog } from '@store/adcm/cluster/mapping/mappingSlice';

export interface ComponentContainerProps {
  componentMapping: ComponentMapping;
  componentMappingValidation: ComponentMappingValidation;
  filter: ServiceMappingFilter;
  allHosts: AdcmHostShortView[];
  onMap: (hosts: AdcmHostShortView[], component: AdcmMappingComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
  allowActions?: AdcmHostComponentMapRuleAction[];
  denyAddHostReason?: React.ReactNode;
  denyRemoveHostReason?: React.ReactNode;
}

const defaultAllowActions = [AdcmHostComponentMapRuleAction.Add, AdcmHostComponentMapRuleAction.Remove];

const ComponentContainer = ({
  componentMapping,
  componentMappingValidation,
  filter,
  allHosts,
  onUnmap,
  onMap,
  denyAddHostReason = <DenyActionTooltip />,
  denyRemoveHostReason = <DenyActionTooltip />,
  allowActions = defaultAllowActions,
}: ComponentContainerProps) => {
  const dispatch = useDispatch();
  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const { component, hosts } = componentMapping;

  const isDisabled = !allowActions?.length;

  const isDenyAdd = !allowActions.includes(AdcmHostComponentMapRuleAction.Add);
  const isDenyRemove = !allowActions.includes(AdcmHostComponentMapRuleAction.Remove);

  const hostsOptions = useMemo<SelectOption<AdcmHostShortView>[]>(
    () =>
      allHosts.map((host) => {
        const isMaintenanceModeOn = host.maintenanceMode === AdcmMaintenanceMode.On;
        return {
          label: host.name,
          value: host,
          disabled: (isDenyRemove && hosts.includes(host)) || isMaintenanceModeOn,
          title: isMaintenanceModeOn ? 'You can not choose a host with maintenance mode is On' : undefined,
        };
      }),
    [allHosts, isDenyRemove, hosts],
  );

  const visibleHosts = useMemo(
    () => hosts.filter((host) => host.name.toLowerCase().includes(filter.hostName.toLowerCase())),
    [filter.hostName, hosts],
  );

  const handleAddClick = () => {
    if (isComponentDependOnNotAddedServices(component, notAddedServicesDictionary)) {
      dispatch(openRequiredServicesDialog(component));
    } else {
      setIsSelectOpen(true);
    }
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
          <div className={s.componentContainerHeader__errors}>
            {!componentMappingValidation.isValid &&
              !componentMappingValidation.constraintsValidationResult.isValid &&
              componentMappingValidation.constraintsValidationResult.errors.map((error) => (
                <MappingError message={error} key={error} />
              ))}
            {!componentMappingValidation.isValid &&
              !componentMappingValidation.requireValidationResults.isValid &&
              componentMappingValidation.requireValidationResults.errors.map((error) => (
                <MappingError message={error} key={error} />
              ))}
          </div>
          <AddMappingButton
            className={s.componentContainerHeader__add}
            ref={addIconRef}
            label="Add hosts"
            onAddClick={handleAddClick}
            denyAddHostReason={denyAddHostReason}
            isDisabled={isDenyAdd}
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
                isDisabled={isDenyRemove}
                denyRemoveHostReason={denyRemoveHostReason}
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

const DenyActionTooltip = () => (
  <div>
    <div>Service of the component must have "Created" state.</div>
    <div>Maintenance mode on the component must be Off</div>
  </div>
);
