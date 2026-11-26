import type { AdcmMapping } from '@models/adcm';
import type { Delta } from '@models/adcm/wizard';

const getMappingPairKey = (item: Pick<AdcmMapping, 'hostId' | 'componentId'>) => `${item.hostId}-${item.componentId}`;

export const diffMapping = (baselineMapping: AdcmMapping[], localMapping: AdcmMapping[]): Delta => {
  const baselinePairKeys = new Set(baselineMapping.map((pair) => getMappingPairKey(pair)));
  const localPairKeys = new Set(localMapping.map((pair) => getMappingPairKey(pair)));

  const add = localMapping
    .filter((pair) => !baselinePairKeys.has(getMappingPairKey(pair)))
    .map(({ hostId, componentId }) => ({ hostId, componentId }));

  const remove = baselineMapping
    .filter((pair) => !localPairKeys.has(getMappingPairKey(pair)))
    .map(({ hostId, componentId }) => ({ hostId, componentId }));

  return { add, remove };
};
