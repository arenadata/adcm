import { memo, useEffect } from 'react';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import FieldNodeContent from './NodeContent/FieldNodeContent';
import AddItemNodeContent from './NodeContent/AddItemNodeContent';
import DefaultNodeContent from './NodeContent/DefaultNodeContent';
import { ConfigurationNode, ConfigurationNodeFilter } from '../ConfigurationEditor.types';
import { buildTreeNodes, filterTreeNodes } from './ConfigurationTree.utils';
import { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { validate } from '@utils/jsonSchemaUtils';
import { ChangeConfigurationNodeHandler, ChangeFieldAttributesHandler } from './ConfigurationTree.types';
import s from './ConfigurationTree.module.scss';
import cn from 'classnames';

export interface ConfigurationTreeProps {
  schema: ConfigurationSchema;
  configuration: ConfigurationData;
  attributes: ConfigurationAttributes;
  filter: ConfigurationNodeFilter;
  onEditField: ChangeConfigurationNodeHandler;
  onAddField: ChangeConfigurationNodeHandler;
  onDeleteField: ChangeConfigurationNodeHandler;
  onAddArrayItem: ChangeConfigurationNodeHandler;
  onDeleteArrayItem: ChangeConfigurationNodeHandler;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onChangeIsValid?: (isValid: boolean) => void;
}

const getNodeClassName = (node: ConfigurationNode, hasError: boolean) =>
  cn(s.collapseNode, {
    [s.collapseNode_failed]: hasError,
  });

const ConfigurationTree = memo(
  ({
    schema,
    configuration,
    attributes,
    filter,
    onEditField,
    onAddField,
    onDeleteField,
    onAddArrayItem,
    onDeleteArrayItem,
    onFieldAttributesChange,
    onChangeIsValid,
  }: ConfigurationTreeProps) => {
    const tree: ConfigurationNode = buildTreeNodes(schema, configuration, attributes);
    const filteredTree = filterTreeNodes(tree, filter);
    const { isValid, errors, errorsPaths } = validate(schema, configuration);
    !isValid && console.error(errors);

    useEffect(() => {
      onChangeIsValid?.(isValid);
    }, [isValid, onChangeIsValid]);

    const handleGetNodeClassName = (node: ConfigurationNode) => {
      const hasError = errorsPaths[node.key] !== undefined;
      return getNodeClassName(node, hasError);
    };

    const handleRenderNodeContent = (node: ConfigurationNode, isExpanded: boolean, onExpand: () => void) => {
      const hasError = typeof errorsPaths[node.key] === 'string';
      switch (node.data.type) {
        case 'field': {
          return (
            <FieldNodeContent node={node} hasError={hasError} onClick={onEditField} onDeleteClick={onDeleteField} />
          );
        }
        case 'addArrayItem': {
          return <AddItemNodeContent node={node} title="1" onClick={onAddArrayItem} />;
        }
        case 'addField': {
          return <AddItemNodeContent node={node} title="Add property" onClick={onAddField} />;
        }
        default: {
          return (
            <DefaultNodeContent
              node={node}
              isExpanded={isExpanded}
              hasError={hasError}
              onDelete={onDeleteArrayItem}
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
