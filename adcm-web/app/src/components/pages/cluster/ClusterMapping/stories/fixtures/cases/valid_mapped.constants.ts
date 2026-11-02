import type { MappingStoryCase } from '../../mappingStory.types';
import { hostAlpha, pairsAlphaZkServer, zkServer } from '../mappingStoryFixtures';

export const validMappedDescription =
  'ZK Server odd constraint with 1 host (alpha): green, host tag, no constraint error.';

export const validMappedCase: MappingStoryCase = {
  description: validMappedDescription,
  kind: 'component',
  pairs: pairsAlphaZkServer,
  components: [zkServer],
  hosts: [hostAlpha],
  focusComponentName: 'zk_server',
};
