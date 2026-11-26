import type { MappingStoryCase } from '../../mappingStory.types';
import { zkServer } from '../mappingStoryFixtures';

export const constraintOddDescription =
  'Constraint [odd]: ZK Server needs an odd host count; 0 hosts: red error; map 1 host (alpha) clears it.';

export const constraintOddCase: MappingStoryCase = {
  description: constraintOddDescription,
  kind: 'component',
  pairs: [],
  components: [zkServer],
  focusComponentName: 'zk_server',
};
