import type { AdcmConcerns } from '@models/adcm/concern';

export const upsertConcern = (concerns: AdcmConcerns[], incoming: AdcmConcerns): AdcmConcerns[] => {
  const index = concerns.findIndex((concern) => concern.id === incoming.id);

  if (index >= 0) {
    const next = [...concerns];
    next[index] = incoming;
    return next;
  }

  return [...concerns, incoming];
};
