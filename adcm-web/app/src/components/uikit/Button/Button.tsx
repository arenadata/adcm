import React from 'react';
import cn from 'classnames';
import s from './Button.module.scss';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon from '@uikit/Icon/Icon';

type ButtonVariant = 'primary' | 'secondary' | 'clear';
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  hasError?: boolean;
  iconLeft?: IconsNames;
  iconRight?: IconsNames;
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
      ...props
    },
    ref,
  ) => {
    const buttonClasses = cn(className, s.button, s[`button_${variant}`], {
      [s.button_error]: hasError,
      [s.button_hasIcon]: !!(iconLeft || iconRight),
    });
    return (
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
    );
  },
);

Button.displayName = 'Button';

export default Button;
