import { useStore } from '@hooks';
import type { SelectOption } from '@uikit';
import { useMemo } from 'react';

export const useAccessManagerPolicyFormDialogWizardStepOne = () => {
  const roles = useStore(({ adcm }) => adcm.policiesActions.relatedData.roles);
  const groups = useStore(({ adcm }) => adcm.policiesActions.relatedData.groups);

  const groupsOptions: SelectOption<number>[] = useMemo(() => {
    return groups.map(({ displayName, id }) => ({ value: id, label: displayName }));
  }, [groups]);

  const rolesOptions: SelectOption<number>[] = useMemo(() => {
    return roles.map(({ displayName, id }) => ({ value: id, label: displayName }));
  }, [roles]);

  return { roles, relatedData: { groupsOptions, rolesOptions } };
};
