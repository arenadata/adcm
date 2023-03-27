import { Component, ContentChild, Input } from '@angular/core';
import { AbstractControl, FormGroup } from '@angular/forms';
import { ADWP_DEFAULT_MATCHER, AdwpMatcher, AdwpStringHandler } from '@app/adwp';
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';
import { RbacPermissionFormComponent } from '../../../components/rbac/permission-form/rbac-permission-form.component';

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

  @Input() readonly = false;

  @ContentChild(RbacPermissionFormComponent) permissionForm: RbacPermissionFormComponent;

  get permissionsControl(): AbstractControl {
    return this.form.controls[this.controlName];
  }

  get selectedPermissions(): RbacRoleModel[] {
    return this.permissionsControl.value || [];
  }

  removeSelectedPermission(item: RbacRoleModel): void {
    const selected = this.permissionsControl.value;
    this.permissionsControl.setValue(selected.filter((i) => i.id !== item.id));
    this.form.markAsDirty();
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

  onBackspaceKeydown(e: KeyboardEvent, chipListInput: HTMLInputElement): void {
    e.stopImmediatePropagation();
    if (!chipListInput.value) {
      e.preventDefault();
      chipListInput.focus();
    }
  }

  reset(control: AbstractControl, chipListInput: HTMLInputElement): void {
    control.reset([]);
    chipListInput.value = '';
    this.permissionForm.value = [] as any;
  }
}
