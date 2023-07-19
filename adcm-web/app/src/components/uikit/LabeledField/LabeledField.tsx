import React, { ReactNode } from 'react';
import s from './LabeledField.module.scss';
import cn from 'classnames';

export interface LabeledFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  disabled?: boolean;
  hint?: ReactNode;
  direction?: 'column' | 'row';
}

const LabeledField = React.forwardRef<HTMLDivElement, LabeledFieldProps>(
  ({ label, hint = '', className, disabled = false, direction = 'column', children, ...props }, ref) => {
    const labeledFieldClasses = cn(
      s.labeledField,
      {
        [s.labeledField_disabled]: disabled,
        [s.labeledField_asRow]: direction === 'row',
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
