import { ChangeDetectionStrategy, Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacUserService } from '@app/services/rbac-user.service';

@Component({
  selector: 'app-rbac-user-form',
  templateUrl: './rbac-user-form.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacUserService) }
  ],
})
export class RbacUserFormComponent extends RbacFormDirective {

  form = new FormGroup({
    id: new FormControl(null),
    is_superuser: new FormControl(null),
    url: new FormControl(null),
    profile: new FormControl(null),
    username: new FormControl(null),
    password: new FormControl(null, [Validators.required, Validators.pattern('[a-zA-Z0-9]*')]),
    first_name: new FormControl(null),
    last_name: new FormControl(null),
    email: new FormControl(null),
    group: new FormControl([])
  });

}
