import { memo, useEffect, useRef, useState } from 'react';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import FieldNodeContent from './NodeContent/FieldNodeContent';
import AddItemNodeContent from './NodeContent/AddItemNodeContent';
import DropPlaceholderNodeContent from './NodeContent/DropPlaceholderNodeContent';
import NodeWithChildrenContent from './NodeContent/NodeWithChildrenContent';
import type {
  ConfigurationNode,
  ConfigurationNodeView,
  ConfigurationArray,
  ConfigurationField,
  ConfigurationTreeFilter,
  ConfigurationObject,
  ConfigurationTreeState,
} from '../ConfigurationEditor.types';
import {
  buildConfigurationNodes,
  buildConfigurationTree,
  buildNodeDictionary,
  getFailedNodeInfo,
  validate,
} from './ConfigurationTree.utils';
import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema, FieldErrors } from '@models/adcm';
import type {
  ChangeConfigurationNodeHandler,
  MoveConfigurationNodeHandler,
  ChangeFieldAttributesHandler,
} from './ConfigurationTree.types';
import s from './ConfigurationTree.module.scss';
import cn from 'classnames';
import { rootNodeKey, toggleAllNodesEventName } from './ConfigurationTree.constants';
import type { JSONPrimitive } from '@models/json';

export interface ConfigurationTreeProps {
  schema: ConfigurationSchema;
  configuration: ConfigurationData;
  attributes: ConfigurationAttributes;
  filter: ConfigurationTreeFilter;
  areExpandedAll: boolean;
  onEditField: ChangeConfigurationNodeHandler;
  onAddEmptyObject: ChangeConfigurationNodeHandler;
  onAddField: ChangeConfigurationNodeHandler;
  onClear: ChangeConfigurationNodeHandler;
  onDelete: ChangeConfigurationNodeHandler;
  onChange: (node: ConfigurationNodeView, value: JSONPrimitive) => void;
  onAddArrayItem: ChangeConfigurationNodeHandler;
  onMoveArrayItem: MoveConfigurationNodeHandler;
  onFieldAttributesChange: ChangeFieldAttributesHandler;
  onChangeIsValid?: (isValid: boolean) => void;
}

const getNodeClassName = (
  node: ConfigurationNodeView,
  hasError: boolean,
  isSelected: boolean,
  isBeforeFailedNode: boolean,
) => {
  const isReadonly = (node.data as ConfigurationArray | ConfigurationObject | ConfigurationField).isReadonly;
  const isDropPlaceholder = node.data.type === 'dropPlaceholder';

  return cn(s.collapseNode, {
    [s.collapseNode_advanced]: !hasError && node.data.fieldSchema.adcmMeta.isAdvanced,
    [s.collapseNode_beforeFailed]: isBeforeFailedNode,
    [s.collapseNode_failed]: hasError,
    [s.collapseNode_disabled]: !hasError && isReadonly,
    [s.isSelected]: isSelected,
    [s.isExpandable]: !!node?.children?.length,
    [s.dropPlaceHolderMode]: isDropPlaceholder,
  });
};

const ConfigurationTree = ({
  schema,
  configuration,
  attributes,
  filter,
  areExpandedAll,
  onEditField,
  onAddEmptyObject,
  onAddField,
  onClear,
  onDelete,
  onChange,
  onAddArrayItem,
  onFieldAttributesChange,
  onMoveArrayItem,
  onChangeIsValid,
}: ConfigurationTreeProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const configNode: ConfigurationNode = buildConfigurationNodes(schema, configuration, attributes);
  const nodeDictionary = buildNodeDictionary(configNode);

  const [treeState, setTreeState] = useState<ConfigurationTreeState>({ dragNode: null, selectedNode: null });

  const viewConfigTree = buildConfigurationTree(configNode, filter, treeState);

  const { isValid, configurationErrors } = validate(schema, configuration, attributes);
  // todo: remove commented for debugging process
  // !isValid && console.error(configurationErrors);

  useEffect(() => {
    onChangeIsValid?.(isValid);
  }, [isValid, onChangeIsValid]);

  useEffect(() => {
    if (ref.current) {
      const eventData = { detail: areExpandedAll };
      ref.current.dispatchEvent(new CustomEvent(toggleAllNodesEventName, eventData));
    }
  }, [areExpandedAll]);

  const handleClick = (node: ConfigurationNodeView, ref: React.RefObject<HTMLElement>) => {
    setTreeState({ ...treeState, selectedNode: node });
    onEditField(node, ref);
  };

  const handleGetNodeClassName = (node: ConfigurationNodeView) => {
    let isBeforeFailedNode = false;
    const hasError = configurationErrors[node.key] !== undefined;
    const isSelected = node.key === treeState.selectedNode?.key;

    const failedNodeInfo = getFailedNodeInfo(nodeDictionary, configurationErrors, node.data.parentNode.key || node.key);
    isBeforeFailedNode = failedNodeInfo ? failedNodeInfo.lastFailedNodeIndex > node.index : false;

    return getNodeClassName(node, hasError, isSelected, isBeforeFailedNode);
  };

  const handleDragStart = (node: ConfigurationNodeView) => {
    setTimeout(() => {
      setTreeState({ ...treeState, dragNode: node });
    }, 100);
  };

  const handleDrop = (dropPlaceHolderNode: ConfigurationNodeView) => {
    if (treeState.dragNode) {
      onMoveArrayItem(treeState.dragNode, dropPlaceHolderNode);
    }
    setTreeState({ ...treeState, dragNode: null });
  };

  const handleDragEnd = (_node: ConfigurationNodeView, isDropped: boolean) => {
    if (!isDropped) {
      setTreeState({ ...treeState, dragNode: null });
    }
  };

  const handleRenderNodeContent = (
    node: ConfigurationNodeView,
    isExpanded: boolean,
    onExpand: (isOpen: boolean) => void,
  ) => {
    const errors =
      typeof configurationErrors[node.key] === 'object' ? (configurationErrors[node.key] as FieldErrors) : undefined;

    switch (node.data.type) {
      case 'field': {
        return (
          <FieldNodeContent
            node={node}
            errors={errors}
            onClick={handleClick}
            onClear={onClear}
            onDelete={onDelete}
            onChange={onChange}
            onFieldAttributeChange={onFieldAttributesChange}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
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
      case 'dropPlaceholder': {
        return <DropPlaceholderNodeContent node={node} onDrop={handleDrop} dataTest="drop-placeholder" />;
      }
      default: {
        return (
          <NodeWithChildrenContent
            node={node}
            isExpanded={isExpanded}
            errors={errors}
            onClear={onClear}
            onDelete={onDelete}
            onExpand={onExpand}
            onFieldAttributeChange={onFieldAttributesChange}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          />
        );
      }
    }
  };

  return (
    <div className={s.collapseNode__root} ref={ref}>
      <CollapseNode
        node={viewConfigTree}
        treeRef={ref}
        isInitiallyExpanded={viewConfigTree.key === rootNodeKey}
        getNodeClassName={handleGetNodeClassName}
        renderNodeContent={handleRenderNodeContent}
      />
    </div>
  );
};

export default memo(ConfigurationTree);
