import { memo, useEffect } from 'react';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import FieldNodeContent from './NodeContent/FieldNodeContent';
import AddItemNodeContent from './NodeContent/AddItemNodeContent';
import NodeWithChildrenContent from './NodeContent/NodeWithChildrenContent';
import {
  ConfigurationArray,
  ConfigurationField,
  ConfigurationNode,
  ConfigurationNodeFilter,
  ConfigurationObject,
} from '../ConfigurationEditor.types';
import { buildTreeNodes, filterTreeNodes, validate } from './ConfigurationTree.utils';
import { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from './ConfigurationTree.types';
import s from './ConfigurationTree.module.scss';
import cn from 'classnames';

export interface ConfigurationTreeProps {
  schema: ConfigurationSchema;
  configuration: ConfigurationData;
  attributes: ConfigurationAttributes;
  filter: ConfigurationNodeFilter;
  onEditField: ChangeConfigurationNodeHandler;
  onAddEmptyObject: ChangeConfigurationNodeHandler;
  onAddField: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onAddArrayItem: ChangeConfigurationNodeHandler;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onChangeIsValid?: (isValid: boolean) => void;
}

const getNodeClassName = (node: ConfigurationNode, hasError: boolean) => {
  const isReadonly = (node.data as ConfigurationArray | ConfigurationObject | ConfigurationField).isReadonly;

  return cn(s.collapseNode, {
    [s.collapseNode_advanced]: !hasError && node.data.fieldSchema.adcmMeta.isAdvanced,
    [s.collapseNode_failed]: hasError,
    [s.collapseNode_disabled]: !hasError && isReadonly,
  });
};

const ConfigurationTree = memo(
  ({
    schema,
    configuration,
    attributes,
    filter,
    onEditField,
    onAddEmptyObject,
    onAddField,
    onDelete,
    onAddArrayItem,
    onFieldAttributesChange,
    onChangeIsValid,
  }: ConfigurationTreeProps) => {
    const tree: ConfigurationNode = buildTreeNodes(schema, configuration, attributes);
    const filteredTree = filterTreeNodes(tree, filter);
    const { isValid, errorsPaths } = validate(schema, configuration, attributes);
    !isValid && console.error(errorsPaths);

    useEffect(() => {
      onChangeIsValid?.(isValid);
    }, [isValid, onChangeIsValid]);

    const handleGetNodeClassName = (node: ConfigurationNode) => {
      const hasError = errorsPaths[node.key] !== undefined;
      return getNodeClassName(node, hasError);
    };

    const handleRenderNodeContent = (node: ConfigurationNode, isExpanded: boolean, onExpand: () => void) => {
      const error = typeof errorsPaths[node.key] === 'string' ? (errorsPaths[node.key] as string) : undefined;
      switch (node.data.type) {
        case 'field': {
          return (
            <FieldNodeContent
              node={node}
              error={error}
              onClick={onEditField}
              onDeleteClick={onDelete}
              onFieldAttributeChange={onFieldAttributesChange}
            />
          );
        }
        case 'addArrayItem': {
          return <AddItemNodeContent node={node} onClick={onAddArrayItem} dataTest="add-array-item" />;
        }
        case 'addField': {
          return <AddItemNodeContent node={node} onClick={onAddField} dataTest="add-field-item" />;
        }
        case 'addEmptyObject': {
          return <AddItemNodeContent node={node} onClick={onAddEmptyObject} dataTest="add-empty-object" />;
        }
        default: {
          return (
            <NodeWithChildrenContent
              node={node}
              isExpanded={isExpanded}
              error={error}
              onDelete={onDelete}
              onExpand={onExpand}
              onFieldAttributeChange={onFieldAttributesChange}
            />
          );
        }
      }
    };

    return (
      <CollapseNode
        node={filteredTree}
        getNodeClassName={handleGetNodeClassName}
        renderNodeContent={handleRenderNodeContent}
      />
    );
  },
);

export default ConfigurationTree;
