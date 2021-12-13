import { Component, Input } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'app-rbac-policy-form-step-two',
  templateUrl: './rbac-policy-form-step-two.component.html',
  styleUrls: ['./rbac-policy-form-step-two.component.scss']
})
export class RbacPolicyFormStepTwoComponent extends BaseFormDirective {
  @Input()
  form: FormGroup;


}
