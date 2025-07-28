import React from 'react';
import cn from 'classnames';
import s from './MultilineInput.module.scss';
import { useFieldStyles } from '@uikit/Field/useFieldStyles';
import type { FieldProps } from '@uikit/Field/Field.types';

export interface MultilineInputProps extends FieldProps, React.HTMLProps<HTMLTextAreaElement> {
  hasError?: boolean;
  containerRef?: React.Ref<HTMLDivElement>;
}

const MultilineInput = React.forwardRef<HTMLTextAreaElement, MultilineInputProps>(
  ({ className, variant = 'primary', hasError, disabled, containerRef, style, ...props }, ref) => {
    const { fieldClasses, fieldContentClasses: inputClasses } = useFieldStyles({ variant, hasError, disabled });

    return (
      <div className={cn(className, fieldClasses)} ref={containerRef} style={style}>
        <textarea ref={ref} className={cn(className, s.multilineInput, inputClasses, 'scroll-rounded')} {...props} />
      </div>
    );
  },
);

export default MultilineInput;
