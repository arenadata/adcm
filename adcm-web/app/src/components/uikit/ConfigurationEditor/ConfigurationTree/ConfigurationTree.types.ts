import { FieldAttributes } from '@models/adcm';
import { ConfigurationNodeView } from '../ConfigurationEditor.types';

export type ChangeConfigurationNodeHandler = (node: ConfigurationNodeView, ref: React.RefObject<HTMLElement>) => void;
export type ChangeFieldAttributesHandler = (path: string, fieldAttributes: FieldAttributes) => void;
