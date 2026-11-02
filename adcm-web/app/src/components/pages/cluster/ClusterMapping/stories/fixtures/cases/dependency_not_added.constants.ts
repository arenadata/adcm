import type { MappingStoryCase } from '../../mappingStory.types';
import { hdfsServicePrototype, zkServerDependingOnHdfs } from '../mappingStoryFixtures';

export const dependencyNotAddedDescription =
  'ZK Server mapped, HDFS missing from cluster: Requires adding (missing service).';

export const dependencyNotAddedCase: MappingStoryCase = {
  description: dependencyNotAddedDescription,
  kind: 'component',
  pairs: [{ hostId: 1, componentId: zkServerDependingOnHdfs.id }],
  components: [zkServerDependingOnHdfs],
  notAddedServicesDictionary: { [hdfsServicePrototype.id]: hdfsServicePrototype },
  focusComponentName: 'zk_server',
};
