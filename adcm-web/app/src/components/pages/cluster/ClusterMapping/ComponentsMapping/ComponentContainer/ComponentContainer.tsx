import { useState, useRef, useMemo } from 'react';
import { Tags } from '@uikit';
import { getOptionsFromArray } from '@uikit/Select/Select.utils';
import MappingItemSelect from '../../MappingItemSelect/MappingItemSelect';
import MappingItemTag from '../../MappingItemTag/MappingItemTag';
import AddMappingButton from '../../AddMappingButton/AddMappingButton';
import MappingError from '../../MappingError/MappingError';
import { AdcmHostShortView, AdcmComponent } from '@models/adcm';
import { ComponentMapping } from '../../ClusterMapping.types';
import { getConstraintsLimit } from '../../ClusterMapping.utils';
import s from './ComponentContainer.module.scss';
import cn from 'classnames';

export interface ComponentContainerProps {
  componentMapping: ComponentMapping;
  allHosts: AdcmHostShortView[];
  onMap: (hosts: AdcmHostShortView[], component: AdcmComponent) => void;
  onUnmap: (hostId: number, componentId: number) => void;
}

const ComponentContainer = ({ componentMapping, allHosts, onUnmap, onMap }: ComponentContainerProps) => {
  const [isSelectOpen, setIsSelectOpen] = useState(false);
  const addIconRef = useRef(null);
  const hostsOptions = useMemo(() => getOptionsFromArray(allHosts, (h) => h.name), [allHosts]);
  const { component, hosts: componentHosts, filteredHosts: visibleHosts, validationSummary } = componentMapping;

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

  const containerClassName = cn(s.componentContainer, s[`componentContainer_${validationSummary}`]);
  const titleClassName = cn(
    s.componentContainerHeader__title,
    s[`componentContainerHeader__title_${validationSummary}`],
  );

  const limit = getConstraintsLimit(component.constraints);

  return (
    <>
      <div className={containerClassName}>
        <div className={s.componentContainerHeader}>
          <span className={titleClassName}>{component.displayName}</span>
          <span className={s.componentContainerHeader__count}>
            {componentHosts.length} / {limit}
          </span>
          {componentMapping.validationSummary !== 'valid' && !componentMapping.constraintsValidationResult.isValid && (
            <MappingError
              message={componentMapping.constraintsValidationResult.error}
              variant={componentMapping.validationSummary}
            />
          )}
          <AddMappingButton
            className={s.componentContainerHeader__add}
            ref={addIconRef}
            label="Add hosts"
            onAddClick={handleAddClick}
          />
        </div>
        {visibleHosts.length > 0 && (
          <Tags className={s.componentContainer__hosts}>
            {visibleHosts.map((host) => (
              <MappingItemTag key={host.id} id={host.id} label={host.name} onDeleteClick={handleDelete} />
            ))}
          </Tags>
        )}
      </div>
      <MappingItemSelect
        isOpen={isSelectOpen}
        checkAllLabel="All hosts"
        searchPlaceholder="Search host"
        options={hostsOptions}
        value={visibleHosts}
        onChange={handleMappingChange}
        onOpenChange={setIsSelectOpen}
        triggerRef={addIconRef}
      />
    </>
  );
};

export default ComponentContainer;
