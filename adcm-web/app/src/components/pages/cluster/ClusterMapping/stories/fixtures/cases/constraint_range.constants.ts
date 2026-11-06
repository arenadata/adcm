import type { MappingStoryCase } from '../../mappingStory.types';
import { withConstraints, zkServer } from '../mappingStoryFixtures';

export const constraintRangeDescription =
  'Constraint [2,3]: 0 hosts: red range error; 2 or 3 hosts valid; 1 host still errors.';

export const constraintRangeCase: MappingStoryCase = {
  description: constraintRangeDescription,
  kind: 'component',
  pairs: [],
  components: [withConstraints(zkServer, [2, 3])],
  focusComponentName: 'zk_server',
};
