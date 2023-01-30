import { Component, EventEmitter, Input, Output } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';
import { ADWP_DEFAULT_MATCHER, AdwpIdentityMatcher, AdwpMatcher } from '@app/adwp';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';

@Component({
  selector: 'app-rbac-policy-form-step-one',
  templateUrl: './rbac-policy-form-step-one.component.html',
  styleUrls: ['./rbac-policy-form-step-one.component.scss']
})
export class RbacPolicyFormStepOneComponent extends BaseFormDirective {
  roleFilter = '';
  userFilter = '';
  groupFilter = '';

  matcher: AdwpMatcher<any> = ADWP_DEFAULT_MATCHER;

  @Input()
  form: FormGroup;

  @Output()
  roleChanged: EventEmitter<void> = new EventEmitter<void>();

  comparator: AdwpIdentityMatcher<RbacRoleModel> = (item1: any, item2: any) => item1?.id === item2?.id;

  isError(name: string): boolean {
    const f = this.form.get(name);
    return f.invalid && (f.dirty || f.touched);
  }

  hasError(error: string): boolean {
    return this.form.hasError(error);
  }
}
