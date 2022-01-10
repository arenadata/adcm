import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';
import { RbacRoleModel } from '../../../../models/rbac/rbac-role.model';

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

export const rbacPolicyObjectValidator = (roleControl: AbstractControl): ValidatorFn => {
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
