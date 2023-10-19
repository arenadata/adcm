import React from 'react';
import { NavLink } from 'react-router-dom';
import s from './Breadcrumbs.module.scss';
import cn from 'classnames';
import { BreadcrumbsItemConfig } from '@routes/routes.types';

interface BreadcrumbsProps {
  list: BreadcrumbsItemConfig[];
  className?: string;
}

const BreadcrumbItem: React.FC<BreadcrumbsItemConfig> = ({ label, href }) => {
  return <li>{href ? <NavLink to={href}>{label}</NavLink> : <span>{label}</span>}</li>;
};

const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ list, className = '' }) => {
  return (
    <nav className={cn(s.breadcrumbs, className)} data-test="breadcrumbs-container">
      <ul>
        {list.map(({ label, href }) => (
          <BreadcrumbItem label={label} href={href} key={label} />
        ))}
      </ul>
    </nav>
  );
};

export default Breadcrumbs;
