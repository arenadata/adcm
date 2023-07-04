import React from 'react';
import cn from 'classnames';
import { PopoverPanelProps } from '@uikit/Popover/Popover.types';
import s from './FormFieldErrorPanel.module.scss';

const FormFieldErrorPanel = React.forwardRef<HTMLDivElement, PopoverPanelProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div ref={ref} {...props} className={cn(className, s.formFieldErrorPanel)}>
        {children}
      </div>
    );
  },
);

export default FormFieldErrorPanel;

FormFieldErrorPanel.displayName = 'FormFieldErrorPanel';
