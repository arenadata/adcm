import type { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import type { AdcmJobStatus, AdcmSubJobLogCheckContentItemWithJobStatus } from '@models/adcm';

export type SubJobLogNode = Node<
  Omit<AdcmSubJobLogCheckContentItemWithJobStatus, 'content'> & { status: AdcmJobStatus }
>;
