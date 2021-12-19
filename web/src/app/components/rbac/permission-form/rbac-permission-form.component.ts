import { Component, Input } from '@angular/core';
import { RbacFormDirective } from '../../../shared/add-component/rbac-form.directive';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';
import { FormGroup } from '@angular/forms';
import { ADWP_DEFAULT_STRINGIFY, adwpDefaultProp, AdwpHandler, AdwpMatcher, AdwpStringHandler } from '@adwp-ui/widgets';

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
  idHandler: AdwpStringHandler<RbacRoleModel>;

  @Input()
  nameHandler: AdwpStringHandler<RbacRoleModel>;

  @Input()
  controlName: string;

  matcher: AdwpMatcher<RbacRoleModel> = (
    item: RbacRoleModel,
    search: RbacRoleModel[],
    stringify: AdwpHandler<RbacRoleModel, string> = ADWP_DEFAULT_STRINGIFY,
  ) => !search.map(stringify).includes(stringify(item));

  save(): void {
    this.form.controls[this.controlName].setValue(this.value);
    this.form.markAsDirty();
  }
}
