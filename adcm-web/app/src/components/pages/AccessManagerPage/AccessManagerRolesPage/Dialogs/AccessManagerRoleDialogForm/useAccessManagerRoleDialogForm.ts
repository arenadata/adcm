import { useStore } from '@hooks';
import { AdcmUpdateRolePayload } from '@models/adcm';

export interface AdcmRoleFormData extends Omit<AdcmUpdateRolePayload, 'children'> {
  children: Set<number>;
}

export const useAccessManagerRoleDialogForm = () => {
  const allPermissions = useStore((s) => s.adcm.rolesActions.relatedData.allRoles);
  const products = useStore((s) => s.adcm.roles.relatedData.categories);

  return {
    relatedData: {
      allPermissions,
      products,
    },
  };
};
