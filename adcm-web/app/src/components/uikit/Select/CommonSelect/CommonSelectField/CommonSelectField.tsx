import React from 'react';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import IconButton from '@uikit/IconButton/IconButton';
import cn from 'classnames';
import s from './CommonSelectField.module.scss';

type CommonSelectFieldProps = Omit<InputProps, 'endAdornment' | 'startAdornment' | 'readOnly' | 'onClick'> & {
  onClick: () => void;
  isOpen: boolean;
};

const CommonSelectField = React.forwardRef<HTMLInputElement, CommonSelectFieldProps>(
  ({ className, onClick, isOpen, ...props }, ref) => {
    const classes = cn(className, s.commonSelectField, { 'is-active': isOpen });
    const handleClick = () => {
      onClick?.();
    };
    return (
      <>
        <Input
          //
          {...props}
          className={classes}
          endAdornment={<IconButton icon="chevron" onClick={handleClick} size={12} />}
          readOnly={true}
          onClick={handleClick}
          ref={ref}
        />
      </>
    );
  },
);
export default CommonSelectField;

CommonSelectField.displayName = 'CommonSelectField';
