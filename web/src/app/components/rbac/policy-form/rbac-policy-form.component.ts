import { Component, forwardRef } from '@angular/core';
import { AbstractControl, FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacPolicyService } from '@app/services/rbac-policy.service';


@Component({
  selector: 'app-rbac-policy-form',
  templateUrl: './rbac-policy-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacPolicyService) }
  ]
})
export class RbacPolicyFormComponent extends RbacFormDirective<RbacPolicyModel> {

  /** Returns a FormArray with the name 'steps'. */
  get steps(): AbstractControl | null { return this.form.get('steps'); }

  form = new FormGroup({
    steps: new FormArray([
      new FormGroup({
        name: new FormControl(null, [Validators.required]),
        description: new FormControl(null),
        role: new FormControl(null),
        user: new FormArray([]),
        group: new FormArray([])
      }),
      new FormGroup({
        object: new FormControl(null)
      })
    ])
  });

  step(id: number): FormGroup | null {
    return this.steps.get([id]) as FormGroup;
  }

}
