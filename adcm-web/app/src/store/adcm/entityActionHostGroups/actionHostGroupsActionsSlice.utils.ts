import { AdcmActionHostGroupHost } from '@models/adcm';

export const splitHosts = (currentHosts: AdcmActionHostGroupHost[], newHostsIds: Set<number>) => {
  const toDelete = new Set<number>();
  const toAdd = new Set(newHostsIds);

  for (const host of currentHosts) {
    if (newHostsIds.has(host.id)) {
      toAdd.delete(host.id);
    } else {
      toDelete.add(host.id);
    }
  }

  return {
    toDelete,
    toAdd,
  };
};
