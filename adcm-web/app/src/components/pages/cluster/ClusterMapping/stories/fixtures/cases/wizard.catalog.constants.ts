import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hostAlpha, hostBeta, hosts, pairsAlphaZkServer } from '../mappingStoryFixtures';
import {
  addOnlyZkServerRules,
  addRemoveZkServerRules,
  emptyRules,
  removeOnlyZkServerRules,
} from './mappingRules.fixtures';

export const wizardRulesAddRemoveCase: MappingStoryCase = {
  description: 'Wizard: Add and Remove on ZK Server. Map and unmap freely on that component.',
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: addRemoveZkServerRules,
};

export const wizardRulesAddOnlyBaselineCase: MappingStoryCase = {
  description: 'Wizard Add-only on ZK Server: alpha unmap blocked; map beta, then unmap beta (undo Add).',
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: addOnlyZkServerRules,
};

export const wizardRulesRemoveOnlyCase: MappingStoryCase = {
  description: 'Wizard Remove-only on ZK Server: cannot add new hosts; alpha can be removed.',
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: removeOnlyZkServerRules,
};

export const wizardRulesNoneOnComponentCase: MappingStoryCase = {
  description: 'Wizard: no rules for any component. Components show not available for mapping.',
  kind: 'wizard',
  pairs: [],
  hosts,
  components,
  rules: emptyRules,
};

export const wizardLayoutEditableFirstCase: MappingStoryCase = {
  description: 'Wizard layout: editable service first: Zookeeper above HBase.',
  kind: 'wizard',
  pairs: [],
  hosts,
  components,
  rules: addRemoveZkServerRules,
};

export const wizardErrorsConstraintMarkerCase: MappingStoryCase = {
  description: 'Wizard: HBase Master unmet constraint: service marker alert.',
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts,
  components,
  rules: addRemoveZkServerRules,
};

export const wizardHostsModeAddOnlyCase: MappingStoryCase = {
  description: 'Wizard hosts mode + Add-only on ZK Server: alpha unmap blocked; map/unmap beta as undo.',
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: addOnlyZkServerRules,
  hostsPreviewMode: true,
};
