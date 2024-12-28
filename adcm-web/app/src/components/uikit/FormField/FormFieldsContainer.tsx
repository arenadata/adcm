import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';
import s from './FormField.module.scss';

const FormFieldsContainer: React.FC<HTMLAttributes<HTMLDivElement>> = ({ children, className, ...props }) => {
  return (
    <div className={cn(className, s.formFieldsContainer)} {...props}>
      {children}
    </div>
  );
};

export default FormFieldsContainer;
