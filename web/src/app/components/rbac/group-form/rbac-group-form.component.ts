import { Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacGroupService } from '@app/services/rbac-group.service';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';
import { CustomValidators } from '../../../shared/validators/custom-validators';

@Component({
  selector: 'app-rbac-group-form',
  templateUrl: './rbac-group-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacGroupService) }
  ]
})
export class RbacGroupFormComponent extends RbacFormDirective<RbacGroupModel> {

  form = new FormGroup({
    id: new FormControl(null),
    name: new FormControl(null, [
      CustomValidators.required,
      Validators.minLength(2),
      Validators.maxLength(150),
      Validators.pattern('^[a-zA-Z0-9()<>{},._-\\s]*$')
    ]),
    description: new FormControl(null),
    user: new FormControl([]),
    url: new FormControl(null),
  });

  ngOnInit() {
    super.ngOnInit();
    this._checkType();
    this.form.markAllAsTouched();
  }

  _checkType() {
    if (this?.value?.type === 'ldap') {
      this.form.controls.name.disable();
      this.form.controls.description.disable();
      this.form.controls.user.disable();
    }
  }
}
