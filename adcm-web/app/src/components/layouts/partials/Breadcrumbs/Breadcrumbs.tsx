import type React from 'react';
import { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import s from './Breadcrumbs.module.scss';
import cn from 'classnames';
import type { BreadcrumbsItemConfig } from '@routes/routes.types';
import { useDispatch } from '@hooks';
import { cleanupBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

interface BreadcrumbsProps {
  list: BreadcrumbsItemConfig[];
  className?: string;
}

const BreadcrumbItem: React.FC<BreadcrumbsItemConfig> = ({ label, href }) => {
  return <li>{href ? <NavLink to={href}>{label}</NavLink> : <span>{label}</span>}</li>;
};

const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ list, className = '' }) => {
  const { pathname } = useLocation();
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(cleanupBreadcrumbs());
  }, [pathname, dispatch]);

  return (
    <nav className={cn(s.breadcrumbs, className)} data-test="breadcrumbs-container">
      <ul>
        {list.map(({ label, href }) => (
          <BreadcrumbItem label={label} href={href} key={label + href} />
        ))}
      </ul>
    </nav>
  );
};

export default Breadcrumbs;
