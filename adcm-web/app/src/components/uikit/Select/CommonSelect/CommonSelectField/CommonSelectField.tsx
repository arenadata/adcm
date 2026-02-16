import React from 'react';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import IconButton from '@uikit/IconButton/IconButton';
import cn from 'classnames';
import s from './CommonSelectField.module.scss';

type CommonSelectFieldProps = Omit<
  InputProps,
  'endAdornment' | 'startAdornment' | 'readOnly' | 'onClick' | 'customContent'
> & {
  onClick: () => void;
  isOpen: boolean;
  customValueRender?: React.ReactNode;
};

const CommonSelectField = React.forwardRef<HTMLInputElement, CommonSelectFieldProps>(
  ({ className, onClick, isOpen, customValueRender, ...props }, ref) => {
    const classes = cn(className, s.commonSelectField, { 'is-active': isOpen });

    return (
      <Input
        {...props}
        className={classes}
        endAdornment={<IconButton icon="chevron" onClick={onClick} size={12} />}
        readOnly={true}
        onClick={onClick}
        ref={ref}
        customContent={customValueRender}
      />
    );
  },
);
export default CommonSelectField;

CommonSelectField.displayName = 'CommonSelectField';
