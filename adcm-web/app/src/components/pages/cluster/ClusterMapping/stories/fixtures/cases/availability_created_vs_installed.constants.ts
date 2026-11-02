import type { MappingStoryCase } from '../../mappingStory.types';
import { hbaseMaster, zkServer } from '../mappingStoryFixtures';

export const availabilityCreatedVsInstalledDescription =
  'HBase Master (installed): Add hosts disabled, tooltip that service must be Created.';

export const availabilityServiceNotCreatedCase: MappingStoryCase = {
  description: availabilityCreatedVsInstalledDescription,
  kind: 'component',
  pairs: [],
  components: [hbaseMaster],
  focusComponentName: 'hbase_master',
};

export const availabilityCreatedServiceCase: MappingStoryCase = {
  description:
    'ZK Server (created): Add hosts enabled; odd constraint may still error until an odd host count is mapped.',
  kind: 'component',
  pairs: [],
  components: [zkServer],
  focusComponentName: 'zk_server',
};
