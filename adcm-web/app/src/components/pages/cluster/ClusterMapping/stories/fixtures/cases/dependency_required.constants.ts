import type { MappingStoryCase } from '../../mappingStory.types';
import { zkClientDependingOnZkServer } from '../mappingStoryFixtures';

export const dependencyRequiredDescription =
  'ZK Client mapped, required ZK Server missing: Requires mapping of components.';

export const dependencyRequiredCase: MappingStoryCase = {
  description: dependencyRequiredDescription,
  kind: 'component',
  pairs: [{ hostId: 1, componentId: zkClientDependingOnZkServer.id }],
  components: [zkClientDependingOnZkServer],
  focusComponentName: 'zk_client',
};
