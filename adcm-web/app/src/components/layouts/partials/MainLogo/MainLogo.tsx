import React, { HTMLAttributes } from 'react';
import { Link } from 'react-router-dom';
import { ReactComponent as FullLogo } from './images/logo.svg';
import { ReactComponent as MiniLogo } from './images/mini-logo.svg';

import s from './MainLogo.module.scss';
import cn from 'classnames';

interface MainLogoProps extends Omit<HTMLAttributes<HTMLAnchorElement>, 'children'> {
  isSmall?: boolean;
}

const MainLogo: React.FC<MainLogoProps> = ({ className, isSmall = false }) => {
  const Logo = isSmall ? MiniLogo : FullLogo;
  return (
    <Link to="/" className={cn(s.mainLogo, className)}>
      <Logo />
    </Link>
  );
};

export default MainLogo;
