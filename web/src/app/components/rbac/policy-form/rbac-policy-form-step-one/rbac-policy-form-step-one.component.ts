import { Component, Input } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';
import { ADWP_DEFAULT_MATCHER, AdwpMatcher } from '@adwp-ui/widgets';

@Component({
  selector: 'app-rbac-policy-form-step-one',
  templateUrl: './rbac-policy-form-step-one.component.html',
  styleUrls: ['./rbac-policy-form-step-one.component.scss']
})
export class RbacPolicyFormStepOneComponent extends BaseFormDirective {
  roleFilter = '';

  matcher: AdwpMatcher<any> = ADWP_DEFAULT_MATCHER;

  @Input()
  form: FormGroup;

}
