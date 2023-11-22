import React from 'react';
import cn from 'classnames';
import s from './Button.module.scss';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon from '@uikit/Icon/Icon';
import { ConditionalWrapper, Tooltip } from '@uikit';
import { TooltipProps } from '@uikit/Tooltip/Tooltip';

type ButtonVariant = 'primary' | 'secondary' | 'clear' | 'tertiary';
export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'title'> {
  variant?: ButtonVariant;
  hasError?: boolean;
  iconLeft?: IconsNames;
  iconRight?: IconsNames;
  title?: TooltipProps['label'];
  tooltipProps?: Omit<TooltipProps, 'label' | 'children'>;
}
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
          {iconLeft && <Icon name={iconLeft} size={28} />}
          {children}
          {iconRight && <Icon name={iconRight} size={28} />}
        </button>
      </ConditionalWrapper>
    );
  },
);

Button.displayName = 'Button';

export default Button;
