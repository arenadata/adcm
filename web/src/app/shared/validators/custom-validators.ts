import { AbstractControl, ValidationErrors } from '@angular/forms';
import { isEmptyObject } from '../../core/types';

export class CustomValidators {
  static required<T extends AbstractControl>(control: T): ValidationErrors | null {
    const value = control.value;
    const error = { 'required': true };
    if (!value) {
      return error;
    }

    if (typeof value === 'string' && value.length === 0) {
      return error;
    }

    if (Array.isArray(value) && value.length === 0) {
      return error;
    }

    if (isEmptyObject(value)) {
      return error;
    }

    return null;
  }

}
