import React, { ReactNode } from 'react';
import s from './LabeledField.module.scss';
import cn from 'classnames';
import { textToDataTestValue } from '@utils/dataTestUtils.ts';

export interface LabeledFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label: ReactNode;
  disabled?: boolean;
  hint?: ReactNode;
  direction?: 'column' | 'row';
  dataTest?: string;
}

const LabeledField = React.forwardRef<HTMLDivElement, LabeledFieldProps>(
  ({ label, hint = '', className, disabled = false, direction = 'column', children, dataTest, ...props }, ref) => {
    const labeledFieldClasses = cn(
      s.labeledField,
      {
        [s.labeledField_disabled]: disabled,
        [s.labeledField_asRow]: direction === 'row',
      },
      className,
    );

    const dataTestValue = dataTest
      ? dataTest
      : (typeof label === 'string' && `field-${textToDataTestValue(label)}`) || 'labeled-field';

    return (
      <div ref={ref} className={labeledFieldClasses} {...props} data-test={dataTestValue}>
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
