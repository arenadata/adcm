import { isHostNameValid, required } from '@utils/validationsUtils';

export const validateSubHostName = (subhostName: string) => {
  if (!required(subhostName)) return 'The subhost name field is required';

  if (!isHostNameValid(subhostName)) return 'The subhost name field is incorrect';

  if (subhostName.length < 2) return 'The subhost name is too short';

  return undefined;
};
