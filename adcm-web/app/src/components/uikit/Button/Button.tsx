import React from 'react';
import cn from 'classnames';
import s from './Button.module.scss';
import type { IconsNames } from '@uikit/Icon/sprite';
import type { IconProps } from '@uikit/Icon/Icon';
import Icon from '@uikit/Icon/Icon';
import type { TooltipProps } from '@uikit/Tooltip/Tooltip';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import Tooltip from '@uikit/Tooltip/Tooltip';

type ButtonVariant = 'primary' | 'secondary' | 'clear' | 'tertiary';

export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'title'> {
  variant?: ButtonVariant;
  hasError?: boolean;
  iconLeft?: IconsNames | IconProps;
  iconRight?: IconsNames | IconProps;
  title?: TooltipProps['label'];
  tooltipProps?: Omit<TooltipProps, 'label' | 'children'>;
  placeholder?: string;
}

const defaultIconProps: Partial<IconProps> = {
  size: 28,
};

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      disabled,
      variant = 'primary',
      hasError = false,
      type = 'button',
      iconLeft,
      iconRight,
      title,
      tooltipProps,
      ...props
    },
    ref,
  ) => {
    const hasIcon = !!(iconLeft || iconRight);
    const buttonClasses = cn(className, s.button, s[`button_${variant}`], {
      [s.button_error]: hasError,
      [s.button_hasIcon]: hasIcon,
      [s.button_hasIconOnly]: !children,
    });

    const calcIconProps = (icon?: IconsNames | IconProps) =>
      !icon
        ? undefined
        : typeof icon === 'string'
          ? { ...defaultIconProps, name: icon }
          : { ...defaultIconProps, ...icon };

    const iconLeftProps = calcIconProps(iconLeft);
    const iconRightProps = calcIconProps(iconRight);

    return (
      <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} {...tooltipProps}>
        <button
          //
          className={buttonClasses}
          disabled={disabled}
          type={type}
          {...props}
          ref={ref}
        >
          {iconLeftProps && <Icon {...iconLeftProps} />}
          {children}
          {iconRightProps && <Icon {...iconRightProps} />}
        </button>
      </ConditionalWrapper>
    );
  },
);

Button.displayName = 'Button';

export default Button;
