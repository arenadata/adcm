import type { ComponentsMappingErrors } from '../../ClusterMapping.types';
import type { AdcmMappingComponent } from '@models/adcm';
import CollapsibleComponentRestrictions from './CollapsibleComponentRestrictions';
import s from './RestrictionsList.module.scss';
import cn from 'classnames';

export interface RestrictionsListProps {
  allComponents: AdcmMappingComponent[];
  mappingErrors: ComponentsMappingErrors;
  onInstallServices: (component: AdcmMappingComponent) => void;
}

const RestrictionsList = (props: RestrictionsListProps) => {
  const { allComponents, mappingErrors } = props;

  const sortedAllComponents = [...allComponents];
  sortedAllComponents.sort((a, b) => a.displayName.localeCompare(b.displayName));

  return (
    <div className={s.restrictionsList}>
      <div className={s.restrictionsList__header}>List of Restrictions</div>
      <div className={cn(s.restrictionsList__content, 'scroll')}>
        {sortedAllComponents.map((component) => {
          const componentErrors = mappingErrors[component.id];
          if (componentErrors === undefined) {
            return null;
          }

          return (
            <CollapsibleComponentRestrictions
              key={component.id}
              component={component}
              errors={componentErrors}
              onInstallServices={() => props.onInstallServices(component)}
            />
          );
        })}
      </div>
    </div>
  );
};

export default RestrictionsList;
