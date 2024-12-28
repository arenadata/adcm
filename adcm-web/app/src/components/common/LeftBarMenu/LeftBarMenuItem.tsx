import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';
import type { To } from 'react-router-dom';
import { useLocation } from 'react-router-dom';
import type { IconsNames } from '@uikit/Icon/sprite';
import Icon from '@uikit/Icon/Icon';
import LinkOrEmpty from '@uikit/LinkOrEmpty/LinkOrEmpty';
import { isCurrentParentPage } from '@utils/urlUtils';
import Tooltip from '@uikit/Tooltip/Tooltip';
import s from './LeftBarMenuItem.module.scss';
import type { MarkerIconType } from '@uikit';
import { ConditionalWrapper, MarkerIcon } from '@uikit';
import type { MarkerVariantType } from '@uikit/MarkerIcon/MarkerIcon.types';

type VariantType = 'default' | 'alert' | 'warning';

const markerOptionsConfig: { [key: string]: { type: MarkerIconType; variant: MarkerVariantType } } = {
  alert: {
    type: 'alert',
    variant: 'square',
  },
  warning: {
    type: 'warning',
    variant: 'square',
  },
};

interface LeftBarMenuItemProps extends HTMLAttributes<HTMLLIElement> {
  icon: IconsNames;
  to?: To;
  isSmall?: boolean;
  variant?: VariantType;
  children: React.ReactNode;
}

const LeftBarMenuItem: React.FC<LeftBarMenuItemProps> = ({
  className,
  to,
  icon,
  children,
  isSmall = false,
  variant = 'default',
  ...props
}) => {
  const { pathname } = useLocation();
  const isActive = to ? isCurrentParentPage(pathname, to) : false;
  const markerOptions = markerOptionsConfig[variant];
  const isMarkerVisible = variant === 'alert';
  const leftBarMenuItemClasses = cn(s.leftBarMenuItem, className, {
    'is-active': isActive,
    [s.leftBarMenuItem__alert]: isMarkerVisible,
  });

  return (
    <li className={leftBarMenuItemClasses} {...props}>
      <LinkOrEmpty to={to}>
        <ConditionalWrapper Component={Tooltip} isWrap={isSmall} label={children} placement={'right'}>
          <button className={s.leftBarMenuItem__button}>
            <Icon name={icon} size={28} />
            {!isSmall && <div>{children}</div>}
            {!isSmall && isMarkerVisible && <MarkerIcon type={markerOptions.type} variant={markerOptions.variant} />}
          </button>
        </ConditionalWrapper>
      </LinkOrEmpty>
    </li>
  );
};

export default LeftBarMenuItem;
