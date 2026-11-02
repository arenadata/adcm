import type { MappingStoryCase } from '../../mappingStory.types';
import { withConstraints, zkServer } from '../mappingStoryFixtures';

export const optionalZeroHostsDescription =
  'Constraint [0,+]: zero hosts is valid; no red constraint error; Add hosts still works.';

export const optionalZeroHostsCase: MappingStoryCase = {
  description: optionalZeroHostsDescription,
  kind: 'component',
  pairs: [],
  components: [withConstraints(zkServer, [0, '+'])],
  focusComponentName: 'zk_server',
};
