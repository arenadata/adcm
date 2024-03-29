import { useMemo } from 'react';
import { Tags } from '@uikit';
import MappingItemTag from '../../MappingItemTag/MappingItemTag';
import { MappingValidation, HostMapping, MappingFilter } from '../../ClusterMapping.types';
import s from './HostContainer.module.scss';
import cn from 'classnames';

export interface HostContainerProps {
  hostMapping: HostMapping;
  mappingValidation: MappingValidation;
  filter: MappingFilter;
  className?: string;
}

const HostContainer = ({ hostMapping, mappingValidation, filter, className }: HostContainerProps) => {
  const { host, components } = hostMapping;

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

  return (
    <>
      <div className={cn(className, s.hostContainer)}>
        <div className={s.hostContainerHeader}>
          <span className={s.hostContainerHeader__title}>{host.name}</span>
          <span className={s.hostContainerHeader__count}>{components.length}</span>
        </div>
        {visibleHostComponents.length > 0 && (
          <Tags className={s.hostContainer__components}>
            {visibleHostComponents.map((c) => (
              <MappingItemTag
                key={c.id}
                id={c.id}
                label={c.displayName}
                validationResult={mappingValidation.byComponents[c.id].constraintsValidationResult}
              />
            ))}
          </Tags>
        )}
      </div>
    </>
  );
};

export default HostContainer;
