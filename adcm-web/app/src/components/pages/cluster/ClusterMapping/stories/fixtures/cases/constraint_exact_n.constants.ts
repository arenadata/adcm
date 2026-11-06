import type { MappingStoryCase } from '../../mappingStory.types';
import { withConstraints, zkServer } from '../mappingStoryFixtures';

export const constraintExactNDescription =
  'Constraint [2]: exactly 2 hosts; 0: red Exactly N error; 1 or 3 keep the error.';

export const constraintExactNCase: MappingStoryCase = {
  description: constraintExactNDescription,
  kind: 'component',
  pairs: [],
  components: [withConstraints(zkServer, [2])],
  focusComponentName: 'zk_server',
};
