import type { InputHTMLAttributes, ReactNode } from 'react';
import { forwardRef } from 'react';
import cn from 'classnames';
import s from './Checkbox.module.scss';
import Icon from '@uikit/Icon/Icon';

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  readOnly?: boolean;
  hasError?: boolean;
}

const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>((props, ref) => {
  const { label, checked = false, disabled = false, className, readOnly = false, hasError = false, ...rest } = props;

  const checkboxClasses = cn(
    s.checkbox,
    {
      [s.checkbox_disabled]: disabled,
      // technically, we can set readonly and disabled. It's strange but if this case then ignore readonly
      [s.checkbox_readonly]: readOnly && !disabled,
      [s.checkbox_error]: hasError,
    },
    className,
  );

  return (
    <label className={checkboxClasses}>
      <input
        className={s.checkbox__input}
        checked={rest.onChange ? checked : undefined}
        defaultChecked={rest.onChange ? undefined : checked}
        ref={ref}
        disabled={disabled || readOnly}
        {...rest}
        type="checkbox"
      />
      <div className={s.checkbox__square}>
        <Icon name="check" className={s.checkbox__mark} size={10} />
      </div>
      {label && <span className={s.checkbox__label}>{label}</span>}
    </label>
  );
});

Checkbox.displayName = 'Checkbox';

export default Checkbox;
