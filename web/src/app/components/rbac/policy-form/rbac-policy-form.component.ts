import { Component, forwardRef, OnInit } from '@angular/core';
import { AbstractControl, FormArray, FormControl, FormGroup, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacPolicyService } from '@app/services/rbac-policy.service';
import { atLeastOne } from '@app/components/rbac/policy-form/rbac-policy-form-step-one/validators/user-or-group-required';
import {
  IRbacObjectCandidateClusterModel,
  IRbacObjectCandidateHostModel,
  IRbacObjectCandidateProviderModel,
  IRbacObjectCandidateServiceModel
} from '../../../models/rbac/rbac-object-candidate';
import { rbacPolicyObjectValidator } from './validators/object-validator';
import { CustomValidators } from '../../../shared/validators/custom-validators';

const INITIAL_OBJECT = {
  cluster: [],
  parent: [],
  service: null,
  provider: [],
  host: []
};

@Component({
  selector: 'app-rbac-policy-form',
  templateUrl: './rbac-policy-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacPolicyService) }
  ]
})
export class RbacPolicyFormComponent extends RbacFormDirective<RbacPolicyModel> implements OnInit {
  static EXPORT_TO_JSON = (value): RbacPolicyModel => {
    if (!value) {
      return null;
    }

    const object = (value.steps[1] && value.steps[1].object) || {};

    const { cluster, parent, provider, host } = object;

    return {
      ...value.steps[0],
      object: [
        ...cluster || [],
        ...parent || [],
        ...provider || [],
        ...host || []
      ]
    };
  };

  initialObject = INITIAL_OBJECT;

  /** Returns a FormArray with the name 'steps'. */
  get steps(): AbstractControl | null { return this.form.get('steps'); }

  get title(): string {
    return this.value ? 'Update' : 'Add';
  }

  step(id: number): FormGroup | null {
    return this.steps.get([id]) as FormGroup;
  }

  ngOnInit() {
    this._createForm();
    this._fillForm(this.value);
    this.form.markAllAsTouched();
  }

  rbacBeforeSave(form: FormGroup): RbacPolicyModel {
    return RbacPolicyFormComponent.EXPORT_TO_JSON(form.value);
  }

  private _fillForm(value: RbacPolicyModel): void {
    if (value) {
      this.form.setValue({
        steps: [
          {
            name: value.name,
            description: value.description || '',
            role: value.role,
            user: value.user,
            group: value.group
          },
          {
            object: {
              cluster: value.object.filter((item: IRbacObjectCandidateClusterModel) => item.type === 'cluster'),
              parent: value.object.reduce((acc: any[], item: IRbacObjectCandidateClusterModel) => [...acc, { id: item.id }], []),
              service: value.object.find((item: IRbacObjectCandidateServiceModel) => item.type === 'service') || '',
              provider: value.object.filter((item: IRbacObjectCandidateProviderModel) => item.type === 'provider'),
              host: value.object.filter((item: IRbacObjectCandidateHostModel) => item.type === 'host'),
            }
          }
        ]
      });
    }
  }

  private _createForm(): void {
    const roleControl = new FormControl(null, [Validators.required]);

    this.form = new FormGroup({
      steps: new FormArray([
        new FormGroup({
          name: new FormControl(null, [
            CustomValidators.required,
            Validators.maxLength(255),
            Validators.minLength(2),
            Validators.pattern('^[a-zA-Z0-9()<>{},._-\\s]*$')
          ]),
          description: new FormControl(null),
          role: roleControl,
          user: new FormControl([]),
          group: new FormControl([])
        }, {
          validators: [atLeastOne('user', 'group')]
        }),
        new FormGroup({
          object: new FormGroup({
            cluster: new FormControl(null, [Validators.required]),
            parent: new FormControl(null, [Validators.required]),
            service: new FormControl(null, [Validators.required]),
            provider: new FormControl(null, [Validators.required]),
            host: new FormControl(null, [Validators.required]),
          }, {
            validators: [
              rbacPolicyObjectValidator(roleControl)
            ]
          })
        })
      ])
    });
  }
}
