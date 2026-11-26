import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hosts } from '../mappingStoryFixtures';

export const layoutClusterAzCase: MappingStoryCase = {
  description: 'Cluster A-Z: services ordered by displayName: HBase, then Zookeeper.',
  kind: 'layout',
  layout: 'cluster_az',
  pairs: [],
  components,
  hosts,
};

export const layoutWizardEditableFirstCase: MappingStoryCase = {
  description: 'Wizard: services with add/remove rules first: Zookeeper (editable), then HBase.',
  kind: 'layout',
  layout: 'wizard_editable_first',
  pairs: [],
  components,
  hosts,
};

export const layoutActionFlatCase: MappingStoryCase = {
  description: 'Dynamic action: flat component list, editable first: ZK Server on top.',
  kind: 'layout',
  layout: 'action_flat',
  pairs: [],
  components,
  hosts,
};
