import React from 'react';
import cn from 'classnames';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon, { IconProps } from '@uikit/Icon/Icon';
import s from './IconButton.module.scss';

type IconButtonVariant = 'primary' | 'secondary';
interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  icon: IconsNames;
  size?: IconProps['size'];
  variant?: IconButtonVariant;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = 32, variant = 'primary', className: outerClassName, ...props }, ref) => {
    const className = cn(outerClassName, s.iconButton, s[`iconButton_${variant}`]);
    return (
      <button className={className} {...props} ref={ref}>
        <Icon name={icon} size={size} />
      </button>
    );
  },
);

IconButton.displayName = 'IconButton';

export default IconButton;
