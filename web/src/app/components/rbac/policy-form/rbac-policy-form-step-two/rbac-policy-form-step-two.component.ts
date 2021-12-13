import { Component, Input, OnInit } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormArray, FormGroup } from '@angular/forms';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';

@Component({
  selector: 'app-rbac-policy-form-step-two',
  templateUrl: './rbac-policy-form-step-two.component.html',
  styleUrls: ['./rbac-policy-form-step-two.component.scss']
})
export class RbacPolicyFormStepTwoComponent extends BaseFormDirective implements OnInit {
  @Input()
  form: FormGroup;

  get role(): RbacRoleModel | null {
    return this.form.parent?.get([0])?.get('role')?.value;
  }

  object(type: 'cluster' | 'service'): FormGroup | null {
    const object = this.form.controls['object'] as FormArray;
    if (type === 'cluster') {
      return object.get([0]) as FormGroup;
    }
    if (type === 'service') {
      return object.get([1]) as FormGroup;
    }
    return null;
  }

  ngOnInit(): void {
  }


}
