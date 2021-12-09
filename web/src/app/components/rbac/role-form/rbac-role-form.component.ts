import { Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { ADD_SERVICE_PROVIDER } from '../../../shared/add-component/add-service-model';
import { RbacRoleService } from '../../../services/rbac-role.service';
import { RbacFormDirective } from '../../../shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';


@Component({
  selector: 'app-rbac-role-form',
  templateUrl: './rbac-role-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacRoleService) }
  ],
})
export class RbacRoleFormComponent extends RbacFormDirective<RbacRoleModel> {

  form = new FormGroup({
    name: new FormControl(null),
    description: new FormControl(null),
    category: new FormControl(['adcm']),
    parametrized_by_type: new FormControl([]),
    child: new FormControl([])
  });

}
