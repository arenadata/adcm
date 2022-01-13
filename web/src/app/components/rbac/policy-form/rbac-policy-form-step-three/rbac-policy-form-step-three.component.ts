import { Component, Input, OnInit } from '@angular/core';
import { BaseFormDirective } from '../../../../shared/add-component';
import { FormGroup } from '@angular/forms';
import { RbacPolicyFormComponent } from '../rbac-policy-form.component';
import { RbacPolicyModel } from '../../../../models/rbac/rbac-policy.model';
import { Observable } from 'rxjs';
import { map, startWith } from 'rxjs/operators';

@Component({
  selector: 'app-rbac-policy-form-step-three',
  templateUrl: './rbac-policy-form-step-three.component.html',
  styleUrls: ['./rbac-policy-form-step-three.component.scss']
})
export class RbacPolicyFormStepThreeComponent extends BaseFormDirective implements OnInit {
  @Input()
  form: FormGroup;

  result$: Observable<RbacPolicyModel>;

  ngOnInit(): void {
    this.result$ = this.form.valueChanges.pipe(
      startWith(this.form.value),
      map(RbacPolicyFormComponent.EXPORT_TO_JSON),
      this.takeUntil()
    );
  }

}
