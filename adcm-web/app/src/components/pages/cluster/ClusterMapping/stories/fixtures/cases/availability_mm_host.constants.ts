import type { MappingStoryCase } from '../../mappingStory.types';
import { hostAlpha, hostGamma, zkServer } from '../mappingStoryFixtures';

export const availabilityMmHostAddDescription =
  'Maintenance mode: gamma On and unmapped: disabled in Add hosts with MM tooltip.';

export const availabilityMmHostAddCase: MappingStoryCase = {
  description: availabilityMmHostAddDescription,
  kind: 'component',
  pairs: [],
  components: [zkServer],
  focusComponentName: 'zk_server',
};

export const availabilityMmHostUnmapDescription =
  'Maintenance mode: gamma On and already mapped: remove (X) stays available.';

export const availabilityMmHostUnmapCase: MappingStoryCase = {
  description: availabilityMmHostUnmapDescription,
  kind: 'component',
  pairs: [
    { hostId: hostAlpha.id, componentId: zkServer.id },
    { hostId: hostGamma.id, componentId: zkServer.id },
  ],
  components: [zkServer],
  focusComponentName: 'zk_server',
};
