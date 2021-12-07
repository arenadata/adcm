import { ChangeDetectionStrategy, Component, forwardRef } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacGroupService } from '@app/services/rbac-group.service';

@Component({
  selector: 'app-rbac-group-form',
  templateUrl: './rbac-group-form.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacGroupService) }
  ],
})
export class RbacGroupFormComponent extends RbacFormDirective {

  form = new FormGroup({
    id: new FormControl(null),
    name: new FormControl(null),
    description: new FormControl(null),
    user: new FormControl([]),
    url: new FormControl(null),
  });

}
