import React from 'react';
import s from './EntityHeader.module.scss';
import cn from 'classnames';

interface EntityHeaderProps {
  title: React.ReactNode;
  subtitle: React.ReactNode;
  central: React.ReactNode;
  actions: React.ReactNode;
  className?: string;
}

const EntityHeader: React.FC<EntityHeaderProps> = ({ className, title, central, actions, subtitle }) => {
  return (
    <div className={cn(s.entityHeader, className, 'ignore-page-padding')}>
      <div className={s.entityHeader__name}>
        <div className={s.entityHeader__title}>{title}</div>
        <div className={s.entityHeader__subtitle}>{subtitle}</div>
      </div>
      <div className={s.entityHeader__central}>{central}</div>
      <div className={s.entityHeader__actions}>{actions}</div>
    </div>
  );
};

export default EntityHeader;
