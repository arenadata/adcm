import { FormGroup, ValidationErrors, ValidatorFn } from '@angular/forms';
import { isEmptyObject } from '../../../../core/types';

export const onlyOne = (firstControlName: string, secondControlName: string): ValidatorFn => (group: FormGroup): ValidationErrors | null => {
  if (!group) {
    return null;
  }

  const firstControl = group.controls[firstControlName];
  const secondControl = group.controls[secondControlName];

  if (!firstControl || !secondControl) {
    return null;
  }

  const value1 = firstControl.value;
  const value2 = secondControl.value;
  const emptyValue = (value: any) => !value || isEmptyObject(value) || (Array.isArray(value) && value.length === 0);

  if (!emptyValue(value1)) {
    secondControl.enabled && secondControl.disable({
      onlySelf: true,
      emitEvent: false
    });
  } else if (!emptyValue(value2)) {
    firstControl.enabled && firstControl.disable({
      onlySelf: true,
      emitEvent: false
    });
  }

  return null;
};
