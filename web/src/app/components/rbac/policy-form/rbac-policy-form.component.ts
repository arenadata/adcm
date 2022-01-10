import { Component, forwardRef, OnInit } from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  ValidationErrors,
  ValidatorFn,
  Validators
} from '@angular/forms';
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
import { RbacRoleModel } from '../../../models/rbac/rbac-role.model';

const INITIAL_OBJECT = {
  cluster: [],
  parent: [],
  service: null,
  provider: [],
  host: []
};

enum StateVariants {
  byCluster = 'byCluster',
  byService = 'byService',
  byProvider = 'byProvider',
}

type PolicyObjectControlsState = {
  [key in StateVariants]: {
    controls: AbstractControl[];
    state: boolean;
  }
}

const objectValidator = (roleControl: AbstractControl): ValidatorFn => {
  let isInitial = true;

  return (objectControl: AbstractControl): ValidationErrors | null => {
    const role: RbacRoleModel | null = roleControl.value;
    if (!role) {
      return null;
    }

    const { parametrized_by_type } = role;

    const variants: StateVariants[] = [StateVariants.byCluster, StateVariants.byService, StateVariants.byProvider];

    const clusterControl = objectControl.get('cluster');
    const serviceControl = objectControl.get('service');
    const parentControl = objectControl.get('parent');
    const providerControl = objectControl.get('provider');
    const hostControl = objectControl.get('host');

    if (isInitial) {
      !clusterControl.disabled && clusterControl.disable();
      !serviceControl.disabled && serviceControl.disable();
      !parentControl.disabled && parentControl.disable();
      !providerControl.disabled && providerControl.disable();
      !hostControl.disabled && hostControl.disable();
    }

    isInitial = false;

    const controlsState: PolicyObjectControlsState = {
      byCluster: {
        controls: [clusterControl],
        state: !!parametrized_by_type.find((v) => v === 'cluster')
      },
      byService: {
        controls: [serviceControl, parentControl],
        state: !!parametrized_by_type.find((v) => v === 'service' || v === 'component')
      },
      byProvider: {
        controls: [providerControl, hostControl],
        state: !!parametrized_by_type.find((v) => v === 'provider')
      },
    };

    variants.forEach((variant) => {
      const stateVariant = controlsState[variant];
      if (stateVariant) {
        stateVariant.controls.forEach((control) => {
          if (stateVariant.state && !control.enabled) {
            control.enable();
          } else if (!stateVariant.state && control.enabled) {
            control.disable();
          }
        });
      }
    });

    if (parametrized_by_type.length === 0) {
      return null;
    }
  };
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

  step(id: number): FormGroup | null {
    return this.steps.get([id]) as FormGroup;
  }

  ngOnInit() {
    this._createForm();
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
    console.log(value);

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

  private _createForm(): void {
    const roleControl = new FormControl(null, [Validators.required]);

    this.form = new FormGroup({
      steps: new FormArray([
        new FormGroup({
          name: new FormControl(null, [Validators.required]),
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
            parent: new FormControl(null),
            service: new FormControl(null, [Validators.required]),
            provider: new FormControl(null, [Validators.required]),
            host: new FormControl(null, [Validators.required]),
          }, {
            validators: [
              objectValidator(roleControl)
            ]
          })
        })
      ])
    });
  }
}
