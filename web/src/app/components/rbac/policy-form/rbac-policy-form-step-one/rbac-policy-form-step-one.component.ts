import { Component, Input } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'app-rbac-policy-form-step-one',
  templateUrl: './rbac-policy-form-step-one.component.html',
  styleUrls: ['./rbac-policy-form-step-one.component.scss']
})
export class RbacPolicyFormStepOneComponent extends BaseFormDirective {
  @Input()
  form: FormGroup;

}
