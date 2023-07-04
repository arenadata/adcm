import React, { useState } from 'react';
import Input, { InputProps } from '@uikit/Input/Input';
import IconButton from '@uikit/IconButton/IconButton';

type InputPasswordProps = Omit<InputProps, 'type' | 'endAdornment' | 'startAdornment'>;

const InputPassword = React.forwardRef<HTMLInputElement, InputPasswordProps>((props, ref) => {
  const [showPassword, setShowPassword] = useState(false);
  const toggleShowPassword = () => {
    setShowPassword((prev) => !prev);
  };

  return (
    <Input
      {...props}
      type={showPassword ? 'text' : 'password'}
      ref={ref}
      endAdornment={
        <IconButton
          type="button"
          icon={showPassword ? 'eye' : 'eye-crossed'}
          size={20}
          onClick={toggleShowPassword}
          disabled={props.disabled}
        />
      }
    />
  );
});
InputPassword.displayName = 'InputPassword';
export default InputPassword;
