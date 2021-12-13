import { FormGroup, ValidatorFn } from '@angular/forms';

export const userOrGroupRequire = (): ValidatorFn => {
  return (formGroup: FormGroup) => {
    const userControl = formGroup.get('user');
    const groupControl = formGroup.get('group');

    if (!userControl || !groupControl) {
      return null;
    }

    const userValue = userControl.value as (any[] | null);
    const groupValue = groupControl.value as (any[] | null);

    if (!userValue?.length && !groupValue?.length) {
      return { userOrGroupRequire: true };
    }

    return null;
  };
};
