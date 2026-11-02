import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hostGamma, zkServer } from '../mappingStoryFixtures';

export const hostsFallbackAfterLocalUnmapCase: MappingStoryCase = {
  description:
    'Hosts mode: gamma (MM On) mapped to ZK Server; after unmap, Add must open again (initiallyMappedComponents fallback).',
  kind: 'hostsMode',
  pairs: [{ hostId: hostGamma.id, componentId: zkServer.id }],
  components,
  hosts: [hostGamma],
};
