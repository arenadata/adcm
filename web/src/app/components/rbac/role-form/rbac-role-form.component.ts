import { Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacRoleService } from '@app/services/rbac-role.service';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '@app/models/rbac/rbac-role.model';

@Component({
  selector: 'app-rbac-role-form',
  templateUrl: './rbac-role-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacRoleService) }
  ],
})
export class RbacRoleFormComponent extends RbacFormDirective<RbacRoleModel> {

  form = new FormGroup({
    id: new FormControl(null),
    name: new FormControl('', [Validators.required]),
    description: new FormControl(''),
    display_name: new FormControl('', [Validators.required]),
    built_in: new FormControl(null),
    type: new FormControl('role'),
    category: new FormControl(['adcm']),
    parametrized_by_type: new FormControl([]),
    child: new FormControl([]),
    url: new FormControl(null),
  });

}
