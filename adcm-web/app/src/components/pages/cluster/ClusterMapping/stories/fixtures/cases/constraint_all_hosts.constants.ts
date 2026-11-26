import type { MappingStoryCase } from '../../mappingStory.types';
import { withConstraints, zkServer } from '../mappingStoryFixtures';

export const constraintAllHostsDescription =
  'Constraint [+]: ZK Server on every host; 0 hosts: red all-hosts error until all listed hosts are mapped.';

export const constraintAllHostsCase: MappingStoryCase = {
  description: constraintAllHostsDescription,
  kind: 'component',
  pairs: [],
  components: [withConstraints(zkServer, ['+'])],
  focusComponentName: 'zk_server',
};
