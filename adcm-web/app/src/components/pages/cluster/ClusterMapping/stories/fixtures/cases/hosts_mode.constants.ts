import type { MappingStoryCase } from '../../mappingStory.types';
import {
  components,
  hbaseMaster,
  hostAlpha,
  hostGamma,
  pairsAlphaZkServer,
  withConstraints,
  zkServer,
} from '../mappingStoryFixtures';

export const hostsModeToggleMappedComponentCase: MappingStoryCase = {
  description: 'Hosts mode: alpha has ZK Server. Open Add click ZK Server again: must unmap, not duplicate.',
  kind: 'hostsMode',
  pairs: pairsAlphaZkServer,
  components,
  hosts: [hostAlpha],
};

export const hostMmOffAddCase: MappingStoryCase = {
  description: 'Host alpha MM Off, empty: Add components active.',
  kind: 'host',
  pairs: [],
  focusHostName: 'alpha',
};

export const hostMmOnDisabledCase: MappingStoryCase = {
  description: 'Host gamma MM On, empty: Add components disabled.',
  kind: 'host',
  pairs: [],
  hosts: [hostGamma],
  focusHostName: 'gamma',
};

export const hostComponentNotCreatedCase: MappingStoryCase = {
  description: 'Host alpha has HBase Master (installed, not Created): X disabled + Created tooltip.',
  kind: 'host',
  pairs: [{ hostId: hostAlpha.id, componentId: hbaseMaster.id }],
  components: [hbaseMaster],
  hosts: [hostAlpha],
  focusHostName: 'alpha',
};

export const hostTagConstraintErrorCase: MappingStoryCase = {
  description: 'Host alpha has ZK Server with exact-2 constraint but only 1 host: red tag.',
  kind: 'host',
  pairs: [{ hostId: hostAlpha.id, componentId: zkServer.id }],
  components: [withConstraints(zkServer, [2])],
  hosts: [hostAlpha],
  focusHostName: 'alpha',
};
