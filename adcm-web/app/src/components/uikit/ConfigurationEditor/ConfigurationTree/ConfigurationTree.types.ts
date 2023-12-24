import { FieldAttributes } from '@models/adcm';
import { ConfigurationNode } from '../ConfigurationEditor.types';

export type ChangeConfigurationNodeHandler = (node: ConfigurationNode, ref: React.RefObject<HTMLElement>) => void;
export type ChangeFieldAttributesHandler = (path: string, fieldAttributes: FieldAttributes) => void;
