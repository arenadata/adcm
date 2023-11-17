import { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import { AdcmJobLogCheckContentItemWithJobStatus } from '@models/adcm';

export type JobLogNode = Node<Omit<AdcmJobLogCheckContentItemWithJobStatus, 'content'>>;
