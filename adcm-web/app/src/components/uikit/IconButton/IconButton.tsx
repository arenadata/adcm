import React from 'react';
import cn from 'classnames';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon, { IconProps } from '@uikit/Icon/Icon';
import s from './IconButton.module.scss';
import { ConditionalWrapper, Tooltip } from '@uikit';
import { TooltipProps } from '@uikit/Tooltip/Tooltip.tsx';

type IconButtonVariant = 'primary' | 'secondary';
export interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'title'> {
  icon: IconsNames;
  size?: IconProps['size'];
  variant?: IconButtonVariant;
  title?: TooltipProps['label'];
  tooltipProps?: Omit<TooltipProps, 'label' | 'children'>;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon, size = 32, variant = 'primary', className: outerClassName, title, tooltipProps, ...props }, ref) => {
    const className = cn(outerClassName, s.iconButton, s[`iconButton_${variant}`]);
    return (
      <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} {...tooltipProps}>
        <button className={className} {...props} ref={ref}>
          <Icon name={icon} size={size} />
        </button>
      </ConditionalWrapper>
    );
  },
);

IconButton.displayName = 'IconButton';

export default IconButton;
