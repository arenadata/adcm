import { Component, forwardRef, OnInit } from '@angular/core';
import { AbstractControl, FormArray, FormControl, FormGroup, ValidatorFn, Validators } from '@angular/forms';
import { RbacFormDirective } from '@app/shared/add-component/rbac-form.directive';
import { RbacPolicyModel } from '@app/models/rbac/rbac-policy.model';
import { ADD_SERVICE_PROVIDER } from '@app/shared/add-component/add-service-model';
import { RbacPolicyService } from '@app/services/rbac-policy.service';
import { atLeastOne } from '@app/components/rbac/policy-form/rbac-policy-form-step-one/validators/user-or-group-required';
import {
  IRbacObjectCandidateClusterModel,
  IRbacObjectCandidateHostModel,
  IRbacObjectCandidateProviderModel
} from '../../../models/rbac/rbac-object-candidate';

const INITIAL_OBJECT = {
  cluster: [],
  parent: [],
  service: null,
  provider: [],
  host: []
};

const clusterOrServiceValidator: ValidatorFn = (control: AbstractControl) => {
  const cluster = control.get('cluster');
  const service = control.get('service');

  if (Array.isArray(cluster.value) && cluster.value.length > 0) {
    service.disable({ onlySelf: true });
  } else {
    service.enable({ onlySelf: true });
  }

  if (!!service.value) {
    cluster.disable({ onlySelf: true });
  } else {
    cluster.enable({ onlySelf: true });
  }

  return null;
};

const providerOrHostValidator: ValidatorFn = (control: AbstractControl) => {
  const provider = control.get('provider');
  const host = control.get('host');

  if (Array.isArray(provider.value) && provider.value.length > 0) {
    host.disable({ onlySelf: true });
  } else {
    host.enable({ onlySelf: true });
  }

  if (Array.isArray(host.value) && host.value.length > 0) {
    provider.disable({ onlySelf: true });
  } else {
    provider.enable({ onlySelf: true });
  }

  return null;
};

@Component({
  selector: 'app-rbac-policy-form',
  templateUrl: './rbac-policy-form.component.html',
  providers: [
    { provide: ADD_SERVICE_PROVIDER, useExisting: forwardRef(() => RbacPolicyService) }
  ]
})
export class RbacPolicyFormComponent extends RbacFormDirective<RbacPolicyModel> implements OnInit {
  initialObject = INITIAL_OBJECT;

  /** Returns a FormArray with the name 'steps'. */
  get steps(): AbstractControl | null { return this.form.get('steps'); }

  form = new FormGroup({
    steps: new FormArray([
      new FormGroup({
        name: new FormControl(null, [Validators.required]),
        description: new FormControl(null),
        role: new FormControl(null, [Validators.required]),
        user: new FormControl([]),
        group: new FormControl([])
      }, {
        validators: [atLeastOne('user', 'group')]
      }),
      new FormGroup({
        object: new FormGroup({
          cluster: new FormControl(null),
          parent: new FormControl(null),
          service: new FormControl(null),
          provider: new FormControl(null),
          host: new FormControl(null),
        }, {
          validators: [clusterOrServiceValidator, providerOrHostValidator]
        })
      })
    ])
  });

  step(id: number): FormGroup | null {
    return this.steps.get([id]) as FormGroup;
  }

  ngOnInit() {
    this._fillForm(this.value);
    this.form.markAllAsTouched();
  }

  rbacBeforeSave(value): RbacPolicyModel {
    const { cluster = [], parent = [], provider = [], host = [] } = value.steps[1].object;

    return {
      ...value.steps[0],
      object: [
        ...cluster,
        ...parent,
        ...provider,
        ...host
      ]
    };
  }

  private _fillForm(value: RbacPolicyModel) {
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
            parent: [],
            service: [],
            provider: value.object.filter((item: IRbacObjectCandidateProviderModel) => item.type === 'provider'),
            host: value.object.filter((item: IRbacObjectCandidateHostModel) => item.type === 'host'),
          }
        }
      ]
    });

  }
}
