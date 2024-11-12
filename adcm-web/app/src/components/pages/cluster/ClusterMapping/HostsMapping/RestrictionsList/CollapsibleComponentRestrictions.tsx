import React, { useState } from 'react';
import type { AdcmMappingComponent } from '@models/adcm';
import { Collapse, Icon } from '@uikit';
import ComponentRestrictions from './ComponentRestrictions';
import type { ComponentMappingErrors } from '../../ClusterMapping.types';
import s from './CollapsibleComponentRestrictions.module.scss';
import cn from 'classnames';

export interface CollapsibleComponentRestrictionsProps {
  component: AdcmMappingComponent;
  errors: ComponentMappingErrors;
  onInstallServices: () => void;
}

const CollapsibleComponentRestrictions = (props: CollapsibleComponentRestrictionsProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleToggle = () => {
    setIsExpanded((prev) => !prev);
  };

  const iconClassName = cn(s.collapsibleComponentRestrictions__icon, {
    ['is-open']: isExpanded,
  });

  return (
    <div className={s.collapsibleComponentRestrictions}>
      <div className={s.collapsibleComponentRestrictions__header}>
        {props.component.displayName}
        <Icon className={iconClassName} size={16} name="chevron" onClick={handleToggle} />
      </div>
      <Collapse isExpanded={isExpanded}>
        <ComponentRestrictions
          className={s.collapsibleComponentRestrictions__list}
          onInstallServices={props.onInstallServices}
          errors={props.errors}
        />
      </Collapse>
    </div>
  );
};

export default CollapsibleComponentRestrictions;
