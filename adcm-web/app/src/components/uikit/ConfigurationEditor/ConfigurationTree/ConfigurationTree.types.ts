import type { FieldAttributes } from '@models/adcm';
import type { ConfigurationNodeView } from '../ConfigurationEditor.types';
import type { JSONValue } from '@models/json';

export type ChangeConfigurationNodeValueHandler = (node: ConfigurationNodeView, value: JSONValue) => void;
export type SelectOneOfBranchHandler = (node: ConfigurationNodeView, selection: string) => void;
export type ChangeConfigurationNodeHandler = (node: ConfigurationNodeView, ref: React.RefObject<HTMLElement>) => void;
export type ChangeFieldAttributesHandler = (path: string, fieldAttributes: FieldAttributes) => void;
export type FieldAttributesSyncPayload = {
  removePaths: string[];
  addPaths: { path: string; fieldAttributes: FieldAttributes }[];
};
export type MoveConfigurationNodeHandler = (
  node: ConfigurationNodeView,
  dropPlaceholder: ConfigurationNodeView,
) => void;
