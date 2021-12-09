import { ChangeDetectionStrategy, Component, forwardRef } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacUserService } from '@app/services/rbac-user.service';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';

/** The password and the confirm password must be equals  */
export const passwordsConfirmValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const password = control.get('user')?.get('password');
  const confirm = control.get('confirm')?.get('password');

  return password && confirm && password.value !== confirm.value ? { passwordsNotMatch: true } : null;
};

@Component({
  selector: 'app-rbac-user-form',
  templateUrl: './rbac-user-form.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacUserService) }
  ],
})
export class RbacUserFormComponent extends RbacFormDirective<RbacUserModel> {
  private _isFirstTouch = true;

  get userForm(): FormGroup {
    return this.form.get('user') as FormGroup;
  }

  get confirmForm(): FormGroup {
    return this.form.get('confirm') as FormGroup;
  }

  form = new FormGroup({
    user: new FormGroup({
      id: new FormControl(null),
      is_superuser: new FormControl(null),
      url: new FormControl(null),
      profile: new FormControl(null),
      username: new FormControl(null),
      password: new FormControl(null, [
        Validators.required, Validators.min(5)
      ]),
      first_name: new FormControl(null),
      last_name: new FormControl(null),
      email: new FormControl(null, [Validators.email]),
      group: new FormControl([])
    }),
    confirm: new FormGroup({
      password: new FormControl('', [
        Validators.required, Validators.min(5)])
    })
  }, { validators: passwordsConfirmValidator });

  ngOnInit(): void {
    this._setValue(this.value);
    this._initPasswordConfirmSubscription();
  }

  rbacBeforeSave(value: any): Partial<RbacUserModel> {
    return this._clearPasswordIfNotTouched(value.user);
  }

  /**
   * As soon as a user focuses an input with password or an input of password confirmation,
   * then in this case we delete the dummy (*****) text
   */
  clearPasswordControlIfFocusIn(): void {
    const forms = Object.values(this.form.controls);

    forms.forEach((form) => {
      if (this._isFirstTouch) {
        form.get('password').setValue('');
        form.updateValueAndValidity();
      }
    });

    this._isFirstTouch = false;
  }

  /**
   * Need to set form value and form value to confirm password
   *
   * @param value
   * @private
   */
  private _setValue(value: RbacUserModel): void {
    if (value) {
      this.userForm.setValue(this.value);
      this.confirmForm.setValue({ password: this.value.password });
    }
  }

  /**
   * An object with a user comes from the server and the password is changed to "*****".
   * If the user does not change anything and submits the form as it is, the password will be sent as "*****".
   * Therefore, before submitting, we delete the key with the password if the user has not touched the form.
   *
   * @param value
   * @private
   */
  private _clearPasswordIfNotTouched(value: RbacUserModel): Partial<RbacUserModel> {
    if (!this.userForm.get('password').touched && !this.confirmForm.get('password').touched) {
      const { password: remove, ...valueWithoutPassword } = value;
      return valueWithoutPassword;
    }

    return value;
  }

  /**
   * Our adwp-input does not know how to work with nested forms, therefore, in this case,
   * it does not display an error message if the control with the password is "invalid".
   * Therefore, we need to manually install and remove the desired error message.
   *
   * @private
   */
  private _initPasswordConfirmSubscription(): void {
    const controls = [this.userForm.get('password'), this.confirmForm.get('password')];

    this.form.statusChanges.subscribe(_ => {
      if (this.form.errors && this.form.errors.passwordsNotMatch) {
        controls.forEach((control) => {
          control.setErrors({ pattern: true }, { emitEvent: false });
        });
      } else {
        controls.forEach((control) => {
          control.setErrors({}, { emitEvent: false });
          control.updateValueAndValidity({ emitEvent: false });
        });
      }
    });
  }
}
