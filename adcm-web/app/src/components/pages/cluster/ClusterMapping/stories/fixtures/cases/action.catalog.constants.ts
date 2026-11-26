import type { MappingStoryCase } from '../../mappingStory.types';
import {
  components,
  hostAlpha,
  hostBeta,
  hostGamma,
  hosts,
  pairsAlphaZkServer,
  zkServer,
} from '../mappingStoryFixtures';
import { addOnlyZkServerRules, addRemoveZkServerRules } from './mappingRules.fixtures';

export const actionFlatEditableFirstCase: MappingStoryCase = {
  description: 'Dynamic action flat list, editable first: ZK Server on top.',
  kind: 'action',
  pairs: [],
  hosts,
  components,
  rules: addRemoveZkServerRules,
};

export const actionRulesAddOnlyBaselineCase: MappingStoryCase = {
  description: 'Dynamic action Add-only on ZK Server: alpha unmap blocked; map beta, then unmap beta.',
  kind: 'action',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: addOnlyZkServerRules,
};

export const actionRulesAddRemoveCase: MappingStoryCase = {
  description: 'Dynamic action: Add and Remove on ZK Server. Map and unmap freely.',
  kind: 'action',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: addRemoveZkServerRules,
};

export const actionEmptyNoServicesCase: MappingStoryCase = {
  description: 'Dynamic action with no components: empty state and link to services page.',
  kind: 'action',
  pairs: [],
  hosts,
  components: [],
  rules: addRemoveZkServerRules,
};

export const actionMmBlockAddCase: MappingStoryCase = {
  description: 'Dynamic action: gamma in MM cannot be added to ZK Server. Add-only rules.',
  kind: 'action',
  pairs: [],
  hosts: [hostAlpha, hostGamma],
  components: [zkServer],
  rules: addOnlyZkServerRules,
};
