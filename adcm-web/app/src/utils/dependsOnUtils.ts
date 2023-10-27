import { AdcmServicePrototype } from '@models/adcm';

export const clearSolvedDependencies = (serviceCandidates: AdcmServicePrototype[]) => {
  // create fast hash
  const allCandidatesSet = new Set(serviceCandidates.map(({ id }) => id));

  return serviceCandidates.map(({ dependOn, ...rest }) => {
    return {
      ...rest,
      // in dependOn can contain dependencies for earlier added services, we should remove it (earlier added services not contain in allCandidatesSet)
      dependOn: dependOn?.filter(({ servicePrototype }) => allCandidatesSet.has(servicePrototype.id)) ?? [],
    };
  });
};
