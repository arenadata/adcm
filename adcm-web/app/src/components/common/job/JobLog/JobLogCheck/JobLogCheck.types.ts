import { Node } from '@uikit/CollapseTree2/CollapseNode.types';
import { AdcmJobLogCheckContentItem } from '@models/adcm';

export type JobLogNode = Node<Omit<AdcmJobLogCheckContentItem, 'content'>>;
