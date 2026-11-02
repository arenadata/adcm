import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hosts, pairsAlphaZkServer } from '../mappingStoryFixtures';

export const clusterComponentsErrorsServiceMarkerCase: MappingStoryCase = {
  description: 'Cluster components: HBase Master unmet (0/1): service marker alert.',
  kind: 'componentsMode',
  pairs: pairsAlphaZkServer,
  components,
  hosts,
};

export const clusterComponentsLayoutNameAzCase: MappingStoryCase = {
  description: 'Cluster layout: services ordered by displayName: HBase, then Zookeeper.',
  kind: 'layout',
  layout: 'cluster_az',
  pairs: [],
  components,
  hosts,
};
