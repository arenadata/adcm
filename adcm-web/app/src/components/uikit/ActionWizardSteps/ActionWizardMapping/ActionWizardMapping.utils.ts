import type { AdcmMapping } from '@models/adcm';
import type { Delta } from '@models/adcm/wizard';

const getKey = (item: AdcmMapping) => `${item.hostId}-${item.componentId}`;

export const applyMappingDelta = (currentMapping: AdcmMapping[], delta: Delta | null): AdcmMapping[] => {
  if (!delta) return currentMapping;
  const { add = [], remove = [] } = delta;
  const map = new Map<string, AdcmMapping>();
  let maxId = 0;

  for (const item of currentMapping) {
    const key = getKey(item);
    map.set(key, item);
    maxId = Math.max(maxId, item.id ?? 0);
  }

  for (const item of remove) {
    map.delete(getKey(item));
  }

  let nextId = maxId + 1;
  for (const item of add) {
    const key = getKey(item);
    if (!map.has(key)) {
      map.set(key, { id: nextId++, hostId: item.hostId, componentId: item.componentId });
    }
  }

  return Array.from(map.values());
};
