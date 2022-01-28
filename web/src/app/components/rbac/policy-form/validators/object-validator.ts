import { AbstractControl, FormGroup, ValidationErrors, ValidatorFn } from '@angular/forms';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';

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

    const controlsState: PolicyObjectControlsState = {
      byCluster: {
        controls: [clusterControl],
        state: !!parametrized_by_type.find((v) => v === 'cluster') && !serviceControl.value
      },
      byService: {
        controls: [serviceControl, parentControl],
        state: !!parametrized_by_type.find((v) => v === 'service' || v === 'component') && !clusterControl.value?.length
      },
      byProvider: {
        controls: [providerControl],
        state: !!parametrized_by_type.find((v) => v === 'provider') && !hostControl.value?.length
      },
      byHost: {
        controls: [hostControl],
        state: !!parametrized_by_type.find((v) => v === 'host') && !providerControl.value?.length
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
