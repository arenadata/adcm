import { Component, Input } from '@angular/core';
import { AbstractControl, FormGroup } from '@angular/forms';
import { AdwpMatcher, AdwpStringHandler } from '@adwp-ui/widgets';
import { ADWP_DEFAULT_MATCHER } from '../../../../../../../adwp_ui/projects/widgets/src/lib/cdk';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';

@Component({
  selector: 'adcm-input-rbac-permission',
  templateUrl: './adcm-input-rbac-permission.component.html',
  styleUrls: ['./adcm-input-rbac-permission.component.scss']
})
export class AdcmInputRbacPermissionComponent {
  @Input() form: FormGroup;

  @Input() controlName: string;

  @Input() multiple: boolean;

  @Input() label: string;

  @Input() nameHandler: AdwpStringHandler<RbacRoleModel>;

  @Input() categoryHandler: AdwpStringHandler<RbacRoleModel>;

  @Input() isRequired = false;

  get permissionsControl(): AbstractControl {
    return this.form.controls[this.controlName];
  }

  get selectedPermissions(): RbacRoleModel[] {
    return this.permissionsControl.value || [];
  }

  removeSelectedPermission(item: RbacRoleModel): void {
    const selected = this.permissionsControl.value;
    this.permissionsControl.setValue(selected.filter((i) => i.id !== item.id));
  }

  open = false;

  matcher: AdwpMatcher<RbacRoleModel> = ADWP_DEFAULT_MATCHER;

  isError(name: string): boolean {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(name: string, error: string): boolean {
    return this.form.controls[name].hasError(error);
  }
}
