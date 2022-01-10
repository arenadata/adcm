import { FormGroup, ValidationErrors, ValidatorFn } from '@angular/forms';

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

  if (value1?.length) {
    secondControl.enabled && secondControl.disable({
      onlySelf: true,
      emitEvent: false
    });
  } else if (value2?.length) {
    firstControl.enabled && firstControl.disable({
      onlySelf: true,
      emitEvent: false
    });
  }

  return null;
};
