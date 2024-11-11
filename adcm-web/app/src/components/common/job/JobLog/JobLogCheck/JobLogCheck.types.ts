import type { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import type { AdcmJobLogCheckContentItemWithJobStatus } from '@models/adcm';

export type JobLogNode = Node<Omit<AdcmJobLogCheckContentItemWithJobStatus, 'content'>>;
