import { Component, Input } from '@angular/core';
import { RbacFormDirective } from '../../../shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';
import { FormGroup } from '@angular/forms';
import { adwpDefaultProp, AdwpStringHandler } from '@adwp-ui/widgets';

@Component({
  selector: 'app-rbac-permission-form',
  templateUrl: './rbac-permission-form.component.html',
  styleUrls: ['./rbac-permission-form.component.scss']
})
export class RbacPermissionFormComponent extends RbacFormDirective<RbacRoleModel> {
  @Input()
  form: FormGroup;

  @Input()
  @adwpDefaultProp()
  options: RbacRoleModel[] = [];

  @Input()
  handler: AdwpStringHandler<RbacRoleModel>;

  @Input()
  controlName: string;

}
