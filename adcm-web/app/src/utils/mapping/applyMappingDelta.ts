import type { AdcmMapping } from '@models/adcm';
import type { Delta } from '@models/adcm/wizard';

const getMappingPairKey = (item: Pick<AdcmMapping, 'hostId' | 'componentId'>) => `${item.hostId}-${item.componentId}`;

export const applyMappingDelta = (currentMapping: AdcmMapping[], delta: Delta | null): AdcmMapping[] => {
  if (!delta) return currentMapping;
  const { add = [], remove = [] } = delta;
  const mappingByPairKey = new Map<string, AdcmMapping>();
  let maxId = 0;

  for (const pair of currentMapping) {
    const pairKey = getMappingPairKey(pair);
    mappingByPairKey.set(pairKey, pair);
    maxId = Math.max(maxId, pair.id ?? 0);
  }

  for (const pair of remove) {
    mappingByPairKey.delete(getMappingPairKey(pair));
  }

  let nextId = maxId + 1;
  for (const pair of add) {
    const pairKey = getMappingPairKey(pair);
    if (!mappingByPairKey.has(pairKey)) {
      mappingByPairKey.set(pairKey, {
        id: nextId++,
        hostId: pair.hostId,
        componentId: pair.componentId,
      });
    }
  }

  return Array.from(mappingByPairKey.values());
};
