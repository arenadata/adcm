import React from 'react';
import s from './EntityHeader.module.scss';
import cn from 'classnames';

interface EntityHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  central?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  dataTest?: string;
}

const EntityHeader: React.FC<EntityHeaderProps> = ({
  className,
  title,
  central,
  actions,
  subtitle,
  dataTest = 'entity-header',
}) => {
  return (
    <div className={cn(s.entityHeader, className, 'ignore-page-padding')} data-test={dataTest}>
      <div className={s.entityHeader__name}>
        <div className={s.entityHeader__title} data-test="entity-header-title">
          {title}
        </div>
        <div className={s.entityHeader__subtitle} data-test="entity-header-sub-title">
          {subtitle}
        </div>
      </div>
      <div className={s.entityHeader__central} data-test="entity-header-additional">
        {central}
      </div>
      <div className={s.entityHeader__actions} data-test="entity-header-actions">
        {actions}
      </div>
    </div>
  );
};

export default EntityHeader;
