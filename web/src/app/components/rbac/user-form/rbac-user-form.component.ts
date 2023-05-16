import { Component, forwardRef } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacUserService } from '@app/services/rbac-user.service';
import { RbacUserModel } from '@app/models/rbac/rbac-user.model';
import { CustomValidators } from '../../../shared/validators/custom-validators';

/** The password and the confirm password must be equals  */
export const passwordsConfirmValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const password = control.get('user')?.get('password');
  const confirm = control.get('confirm')?.get('password');

  return password && confirm && password.value !== confirm.value ? { passwordsNotMatch: true } : null;
};

@Component({
  selector: 'app-rbac-user-form',
  templateUrl: './rbac-user-form.component.html',
  styleUrls: ['rbac-user-form.component.scss'],
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacUserService) }
  ]
})
export class RbacUserFormComponent extends RbacFormDirective<RbacUserModel> {
  private _isFirstTouch = true;
  passMinLength = null;
  passMaxLength = null;
  form: FormGroup = new FormGroup({
    user: new FormGroup({
      id: new FormControl(null),
      is_superuser: new FormControl(null),
      built_in: new FormControl(null),
      url: new FormControl(null),
      profile: new FormControl(null),
      username: new FormControl(null, [
        CustomValidators.required,
        Validators.minLength(2),
        Validators.maxLength(150),
        Validators.pattern('^[a-zA-Z0-9_.-\/]*$')
      ]),
      password: new FormControl(null, [
        CustomValidators.required
      ]),
      first_name: new FormControl(null, [
        CustomValidators.required,
        Validators.minLength(2),
        Validators.maxLength(150),
        Validators.pattern('^[a-zA-Z\\s]*$')
      ]),
      last_name: new FormControl(null, [
        CustomValidators.required,
        Validators.minLength(2),
        Validators.maxLength(150),
        Validators.pattern('^[a-zA-Z\\s]*$')
      ]),
      email: new FormControl(null, [
        CustomValidators.required,
        Validators.maxLength(254),
        // regexp from django
        Validators.pattern('(^[-!#$%&\'*+\\/=?^_`{}|~0-9A-Za-z]+(.[-!#$%&\'*+\\/=?^_`{}|~0-9A-Za-z]+)*|^"([\\001-\\010\\013\\014\\016-\\037!#-[]-\\177]|\\[\\001-\\011\\013\\014\\016-\\177])*")@((?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?.)+)(?:[A-Za-z0-9-]{2,63}(?<!-))$')
      ]),
      group: new FormControl([])
    }),
    confirm: new FormGroup({
      password: new FormControl(null, [
        CustomValidators.required
      ])
    })
  }, { validators: passwordsConfirmValidator });

  isDisabled = (value) => {
    return value?.type === 'ldap';
  };

  get passwordValidators() {
    return [
      ... !this.value ? [Validators.required] : [],
      Validators.minLength(this.passMinLength || 3),
      Validators.maxLength(this.passMaxLength || 128),
      Validators.pattern(new RegExp(/^[\s\S]*$/u))
    ]
  }

  get userForm(): FormGroup {
    return this.form.get('user') as FormGroup;
  }

  get confirmForm(): FormGroup {
    return this.form.get('confirm') as FormGroup;
  }

  ngOnInit(): void {
    this.getGlobalSettings().subscribe((resp) => {
      this.passMinLength = resp.config['auth_policy'].min_password_length;
      this.passMaxLength = resp.config['auth_policy'].max_password_length;

      this._setValue(this.value);
      this._initPasswordConfirmSubscription();
      this.form.markAllAsTouched();
    })
  }

  rbacBeforeSave(form: FormGroup): Partial<RbacUserModel> {
    return this.getDirtyValues(form);
  }

  getDirtyValues(data) {
    const user = data?.controls['user']?.controls;
    const result = {};

    Object.keys(user).forEach((key) => {
      if (user[key].dirty && user[key].value !== '') {
        result[key] = user[key]?.value;
      }
    })

    return result;
  }

  /** Add password length validators only if we are going to change it
   * because password length rules could be changed anytime
   */
  onFocus() {
    this.clearPasswordControlIfFocusIn();
    this.addPasswordValidators();
  }

  addPasswordValidators() {
    const userForm: Partial<FormGroup> = this.form.controls.user;
    const confirmForm: Partial<FormGroup> = this.form.controls.confirm;
    userForm.controls['password'].setValidators(this.passwordValidators);
    confirmForm.controls['password'].setValidators(this.passwordValidators);
    this.form.updateValueAndValidity();
  }

  /**
   * As soon as a user focuses an input with password or an input of password confirmation,
   * then in this case we delete the dummy (*****) text
   */
  clearPasswordControlIfFocusIn(): void {
    const forms = Object.values(this.form.controls);

    forms.forEach((form: AbstractControl) => {
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
      const type: string = this.value?.type;
      // ToDo(lihih) the "adwp-list" should not change the composition of the original model.
      //  Now he adds the "checked" key to the model
      this._updateAndSetValueForForm(this.userForm);
      this.confirmForm.setValue({ password: '******' }); // read commentary inside _updateAndSetValueForForm
      this.form.get('user.username').disable();

      if (type === 'ldap' || value?.is_active === false) {
        this.userForm.controls.first_name.disable();
        this.userForm.controls.last_name.disable();
        this.userForm.controls.email.disable();
        this.userForm.controls.password.disable();
        this.confirmForm.controls.password.disable();
      }

      if (value?.is_active === false) {
        this.userForm.controls.group.disable();
        this.userForm.controls.is_superuser.disable();
      }
    }
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
          control.setErrors({ passwordsNotMatch: true }, { emitEvent: false });
        });
      } else {
        controls.forEach((control) => {
          control.setErrors({}, { emitEvent: false });
          control.updateValueAndValidity({ emitEvent: false });
        });
      }
    });
  }

  _isUserNotActive(value) {
    return value?.is_active === false;
  }

  _updateAndSetValueForForm(form) {
    const formValue = { ...this.value };
    Object.keys(formValue).forEach((prop) => {
      if (!form.controls.hasOwnProperty(prop)) delete formValue[prop];
    })

    formValue.password = '******'; // password will not be provided from backend, but we still need to use it in formControl

    form.setValue(formValue);
  }
}
