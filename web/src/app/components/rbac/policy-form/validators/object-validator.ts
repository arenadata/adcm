import { AbstractControl, FormGroup, ValidationErrors, ValidatorFn } from '@angular/forms';
import { RbacRoleModel, RbacRoleParametrizedBy } from '../../../../models/rbac/rbac-role.model';
import { ParametrizedPipe } from '../rbac-policy-form-step-two/pipes/parametrized.pipe';

enum StateVariants {
  byCluster = 'byCluster',
  byService = 'byService',
  byProvider = 'byProvider',
  byHost = 'byHost',
}

type PolicyObjectControlsState = {
  [key in StateVariants]: {
    controls: AbstractControl[];
    state: boolean;
  }
}

export const rbacPolicyObjectValidator = (roleControl: AbstractControl): ValidatorFn => {
  return (objectControl: FormGroup): ValidationErrors | null => {
    const role: RbacRoleModel | null = roleControl.value;
    if (!role) {
      return null;
    }

    const { parametrized_by_type } = role;

    const variants: StateVariants[] = [StateVariants.byCluster, StateVariants.byService, StateVariants.byProvider, StateVariants.byHost];

    const clusterControl = objectControl.controls['cluster'];
    const serviceControl = objectControl.controls['service'];
    const parentControl = objectControl.controls['parent'];
    const providerControl = objectControl.controls['provider'];
    const hostControl = objectControl.controls['host'];

    const parametrizedByToState = (...cases: (RbacRoleParametrizedBy | RbacRoleParametrizedBy[])[]) => new ParametrizedPipe().transform(role, ...cases);

    const controlsState: PolicyObjectControlsState = {
      byCluster: {
        controls: [clusterControl],
        state: parametrizedByToState(['cluster']) && !serviceControl.value
      },
      byService: {
        controls: [serviceControl, parentControl],
        state: parametrizedByToState(['service'], ['component']) && !clusterControl.value?.length
      },
      byProvider: {
        controls: [providerControl],
        state: parametrizedByToState(['provider']) && !hostControl.value?.length

      },
      byHost: {
        controls: [hostControl],
        state: parametrizedByToState('host', ['host', 'provider']) && !providerControl.value?.length
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
