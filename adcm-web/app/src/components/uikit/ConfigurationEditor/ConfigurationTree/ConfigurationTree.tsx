import { memo, useEffect, useState } from 'react';
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
import { rootNodeKey } from './ConfigurationTree.constants';

export interface ConfigurationTreeProps {
  schema: ConfigurationSchema;
  configuration: ConfigurationData;
  attributes: ConfigurationAttributes;
  filter: ConfigurationNodeFilter;
  onEditField: ChangeConfigurationNodeHandler;
  onAddEmptyObject: ChangeConfigurationNodeHandler;
  onAddField: ChangeConfigurationNodeHandler;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onAddArrayItem: ChangeConfigurationNodeHandler;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onChangeIsValid?: (isValid: boolean) => void;
}

const getNodeClassName = (node: ConfigurationNode, hasError: boolean, isSelected: boolean) => {
  const isReadonly = (node.data as ConfigurationArray | ConfigurationObject | ConfigurationField).isReadonly;

  return cn(s.collapseNode, {
    [s.collapseNode_advanced]: !hasError && node.data.fieldSchema.adcmMeta.isAdvanced,
    [s.collapseNode_failed]: hasError,
    [s.collapseNode_disabled]: !hasError && isReadonly,
    [s.isSelected]: isSelected,
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
    onClear,
    onDelete,
    onAddArrayItem,
    onFieldAttributesChange,
    onChangeIsValid,
  }: ConfigurationTreeProps) => {
    const tree: ConfigurationNode = buildTreeNodes(schema, configuration, attributes);
    const [selectedNode, setSelectedNode] = useState<ConfigurationNode | null>(null);
    const filteredTree = filterTreeNodes(tree, filter);
    const { isValid, errorsPaths } = validate(schema, configuration, attributes);
    // todo: remove commented for debugging process
    // !isValid && console.error(errorsPaths);

    useEffect(() => {
      onChangeIsValid?.(isValid);
    }, [isValid, onChangeIsValid]);

    const handleClick = (node: ConfigurationNode, ref: React.RefObject<HTMLElement>) => {
      setSelectedNode(node);
      onEditField(node, ref);
    };

    const handleGetNodeClassName = (node: ConfigurationNode) => {
      const hasError = errorsPaths[node.key] !== undefined;
      const isSelected = node.key === selectedNode?.key;
      return getNodeClassName(node, hasError, isSelected);
    };

    const handleRenderNodeContent = (
      node: ConfigurationNode,
      isExpanded: boolean,
      onExpand: (isOpen: boolean) => void,
    ) => {
      const error = typeof errorsPaths[node.key] === 'string' ? (errorsPaths[node.key] as string) : undefined;
      switch (node.data.type) {
        case 'field': {
          return (
            <FieldNodeContent
              node={node}
              error={error}
              onClick={handleClick}
              onClear={onClear}
              onDelete={onDelete}
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
              onClear={onClear}
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
        isInitiallyExpanded={filteredTree.key === rootNodeKey}
        getNodeClassName={handleGetNodeClassName}
        renderNodeContent={handleRenderNodeContent}
      />
    );
  },
);

export default ConfigurationTree;
