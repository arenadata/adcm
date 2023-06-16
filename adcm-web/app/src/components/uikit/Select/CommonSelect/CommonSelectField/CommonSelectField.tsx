import React from 'react';
import Input, { InputProps } from '@uikit/Input/Input';
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
      <Input
        //
        {...props}
        className={classes}
        endAdornment={<IconButton icon="chevron" onClick={handleClick} size={14} />}
        readOnly={true}
        ref={ref}
        onClick={handleClick}
      />
    );
  },
);
export default CommonSelectField;

CommonSelectField.displayName = 'CommonSelectField';
