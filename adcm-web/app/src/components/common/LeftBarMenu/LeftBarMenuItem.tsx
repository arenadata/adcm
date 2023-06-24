import React, { HTMLAttributes } from 'react';
import cn from 'classnames';
import { To, useLocation } from 'react-router-dom';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon from '@uikit/Icon/Icon';
import LinkOrEmpty from '@uikit/LinkOrEmpty/LinkOrEmpty';
import { isCurrentPathname } from '@uikit/utils/urlUtils';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import Tooltip from '@uikit/Tooltip/Tooltip';

import s from './LeftBarMenuItem.module.scss';

interface LeftBarMenuItemProps extends HTMLAttributes<HTMLLIElement> {
  icon: IconsNames;
  to?: To;
  isSmall?: boolean;
  children: React.ReactNode;
}

const LeftBarMenuItem: React.FC<LeftBarMenuItemProps> = ({
  className,
  to,
  icon,
  children,
  isSmall = false,
  ...props
}) => {
  const { pathname } = useLocation();
  const isActive = to ? isCurrentPathname(pathname, to) : false;
  return (
    <li className={cn(s.leftBarMenuItem, className, { 'is-active': isActive })} {...props}>
      <LinkOrEmpty to={to}>
        <ConditionalWrapper Component={Tooltip} isWrap={isSmall} label={children} placement={'right'}>
          <button className={s.leftBarMenuItem__button}>
            <Icon name={icon} size={28} />
            {!isSmall && <div>{children}</div>}
          </button>
        </ConditionalWrapper>
      </LinkOrEmpty>
    </li>
  );
};

export default LeftBarMenuItem;
