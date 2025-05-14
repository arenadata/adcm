import type { FieldAttributes } from '@models/adcm';
import type { ConfigurationNodeView } from '../ConfigurationEditor.types';

export type ChangeConfigurationNodeHandler = (node: ConfigurationNodeView, ref: React.RefObject<HTMLElement>) => void;
export type ChangeFieldAttributesHandler = (path: string, fieldAttributes: FieldAttributes) => void;
export type MoveConfigurationNodeHandler = (
  node: ConfigurationNodeView,
  dropPlaceholder: ConfigurationNodeView,
) => void;
