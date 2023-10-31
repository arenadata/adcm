import { FieldProps } from './Field.types';
import s from './Field.module.scss';
import cn from 'classnames';

export const useFieldStyles = ({ variant = 'primary', disabled, hasError }: FieldProps) => {
  const fieldClasses = cn(s.field, s[`field_${variant}`], {
    [s.field_error]: hasError,
    [s.field_disabled]: disabled,
  });
  const fieldContentClasses = s.field__mainContent;

  return {
    fieldClasses,
    fieldContentClasses,
  };
};
