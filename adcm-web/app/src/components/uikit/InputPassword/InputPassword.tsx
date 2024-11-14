import type { FocusEvent } from 'react';
import React, { useState } from 'react';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import IconButton from '@uikit/IconButton/IconButton';

interface InputPasswordProps extends Omit<InputProps, 'type' | 'endAdornment' | 'startAdornment'> {
  areAsterisksShown?: boolean;
}

const dummyPasswordValue = '******';

const InputPassword = React.forwardRef<HTMLInputElement, InputPasswordProps>(
  ({ areAsterisksShown = false, placeholder, ...props }, ref) => {
    const [isPasswordShown, setIsPasswordShown] = useState(false);
    const [passwordPlaceholder, setPasswordPlaceholder] = useState(dummyPasswordValue);

    const toggleShowPassword = () => {
      setIsPasswordShown((prev) => !prev);
    };

    const focusHandler = (e: FocusEvent<HTMLInputElement>) => {
      if (areAsterisksShown) {
        setPasswordPlaceholder('');
      }

      props.onFocus?.(e);
    };

    const blurHandler = (e: FocusEvent<HTMLInputElement>) => {
      if (areAsterisksShown) {
        setPasswordPlaceholder(dummyPasswordValue);
      }

      props.onBlur?.(e);
    };

    return (
      <Input
        {...props}
        type={isPasswordShown ? 'text' : 'password'}
        ref={ref}
        placeholder={!areAsterisksShown ? placeholder : passwordPlaceholder}
        onFocus={focusHandler}
        onBlur={blurHandler}
        endAdornment={
          <IconButton
            type="button"
            icon={isPasswordShown ? 'eye' : 'eye-crossed'}
            size={20}
            onClick={toggleShowPassword}
            disabled={props.disabled}
            tabIndex={-1}
          />
        }
      />
    );
  },
);
InputPassword.displayName = 'InputPassword';
export default InputPassword;
