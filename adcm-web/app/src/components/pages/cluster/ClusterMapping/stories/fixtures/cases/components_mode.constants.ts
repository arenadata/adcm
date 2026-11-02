import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hdfsServicePrototype, hosts, zkServerDependingOnHdfs } from '../mappingStoryFixtures';

export const componentsModeOverviewCase: MappingStoryCase = {
  description: 'Components mode: two services, constraints/availability as on the cluster page.',
  kind: 'componentsMode',
  pairs: [],
  components,
  hosts,
};

export const componentsModeNotAddedCase: MappingStoryCase = {
  description: 'Components mode: ZK Server mapped and depends on missing HDFS.',
  kind: 'componentsMode',
  pairs: [{ hostId: 1, componentId: zkServerDependingOnHdfs.id }],
  components: [zkServerDependingOnHdfs],
  notAddedServicesDictionary: { [hdfsServicePrototype.id]: hdfsServicePrototype },
};
