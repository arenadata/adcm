import type { MappingStoryCase } from '../../mappingStory.types';
import { components, hostAlpha, hostBeta, pairsAlphaZkServer } from '../mappingStoryFixtures';
import { addOnlyZkServerRules } from './mappingRules.fixtures';

export const wizardAddOnlyZkServerRules = addOnlyZkServerRules;

export const wizardAddOnlyBaselineDescription =
  'Wizard Add-only on ZK Server: alpha mapped (unmap blocked); map beta, then unmap beta (undo Add).';

export const wizardAddOnlyBaselineCase: MappingStoryCase = {
  description: wizardAddOnlyBaselineDescription,
  kind: 'wizard',
  pairs: pairsAlphaZkServer,
  hosts: [hostAlpha, hostBeta],
  components,
  rules: wizardAddOnlyZkServerRules,
};
