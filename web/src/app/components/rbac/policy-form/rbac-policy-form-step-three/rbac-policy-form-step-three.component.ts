import { Component, Input } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'app-rbac-policy-form-step-three',
  templateUrl: './rbac-policy-form-step-three.component.html',
  styleUrls: ['./rbac-policy-form-step-three.component.scss']
})
export class RbacPolicyFormStepThreeComponent extends BaseFormDirective {
  @Input()
  form: FormGroup;

}
