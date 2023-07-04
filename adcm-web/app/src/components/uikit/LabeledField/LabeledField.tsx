import React, { ReactNode } from 'react';
import s from './LabeledField.module.scss';
import cn from 'classnames';

export interface LabeledFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  disabled?: boolean;
  hint?: ReactNode;
}

const LabeledField = React.forwardRef<HTMLDivElement, LabeledFieldProps>(
  ({ label, hint = '', className, disabled = false, children, ...props }, ref) => {
    const labeledFieldClasses = cn(
      s.labeledField,
      {
        [s.labeledField_disabled]: disabled,
      },
      className,
    );

    return (
      <div ref={ref} className={labeledFieldClasses} {...props}>
        <div className={s.labeledField__labelWrap}>
          <label className={s.labeledField__label}>{label}</label>
          {hint}
        </div>
        {children}
      </div>
    );
  },
);

export default LabeledField;
