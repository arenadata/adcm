import { FormGroup, ValidationErrors, ValidatorFn } from '@angular/forms';

export const atLeastOne = (firstControlName: string, secondControlName: string): ValidatorFn => (group: FormGroup): ValidationErrors | null => {
  if (!group) {
    return null;
  }

  const firstControl = group.controls[firstControlName];
  const secondControl = group.controls[secondControlName];

  if (!firstControl || !secondControl) {
    return null;
  }

  const userValue = firstControl.value;
  const groupValue = secondControl.value;

  if (!userValue?.length && !groupValue?.length) {
    firstControl.setErrors({ required: true }, { emitEvent: false });
    secondControl.setErrors({ required: true }, { emitEvent: false });
    firstControl.markAsDirty({ onlySelf: true });
    secondControl.markAsDirty({ onlySelf: true });
    return { required: true };
  } else {
    firstControl.setErrors(null);
    secondControl.setErrors(null);
    firstControl.updateValueAndValidity({ onlySelf: true });
    secondControl.updateValueAndValidity({ onlySelf: true });
  }

  return null;
};
