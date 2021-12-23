import { Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacGroupService } from '@app/services/rbac-group.service';
import { RbacGroupModel } from '@app/models/rbac/rbac-group.model';

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
      Validators.required,
      Validators.minLength(1),
      Validators.maxLength(150),
      Validators.pattern('^[a-zA-Z_]*$')
    ]),
    description: new FormControl(null),
    user: new FormControl([]),
    url: new FormControl(null),
  });

}
