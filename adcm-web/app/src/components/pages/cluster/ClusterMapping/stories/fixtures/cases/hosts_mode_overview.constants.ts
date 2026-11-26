import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hosts } from '../mappingStoryFixtures';

export const hostsModeOverviewCase: MappingStoryCase = {
  description: 'Hosts mode: host cards + List of Restrictions (unmapped odd ZK Server).',
  kind: 'hostsMode',
  pairs: [],
  components,
  hosts,
};
