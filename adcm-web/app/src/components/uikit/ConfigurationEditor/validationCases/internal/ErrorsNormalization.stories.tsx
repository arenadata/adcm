import { useRef, useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import type { ConfigurationAttributes, SchemaDefinition } from '@models/adcm';
import type { JSONObject } from '@models/json';
import type {
  ConfigurationNode,
  ConfigurationNodeView,
  ConfigurationTreeFilter,
  ConfigurationTreeState,
  ConfigurationField,
  ConfigurationArray,
  ConfigurationObject,
} from '../../ConfigurationEditor.types';
import FieldNodeContent from '../../ConfigurationTree/NodeContent/FieldNodeContent';
import NodeWithChildrenContent from '../../ConfigurationTree/NodeContent/NodeWithChildrenContent/NodeWithChildrenContent';
import {
  buildConfigurationNodes,
  buildConfigurationTree,
  buildNodeDictionary,
  getErrorsForTreeRow,
  getFailedNodeInfo,
} from '../../ConfigurationTree/ConfigurationTree.utils';
import s from '../../ConfigurationTree/ConfigurationTree.module.scss';
import cn from 'classnames';
import { rootNodeKey } from '../../ConfigurationTree/ConfigurationTree.constants';
import { jsonSchemaValidationService } from '@utils/jsonSchema/JsonSchemaValidationService';

type StoryArgs = Record<string, never>;

const meta = {
  title: 'uikit/ConfigurationEditor/ValidationCases/Internal/Errors normalization',
} satisfies Meta<StoryArgs>;

export default meta;
type Story = StoryObj<StoryArgs>;

const getNodeClassName = (
  node: ConfigurationNodeView,
  hasError: boolean,
  isSelected: boolean,
  isBeforeFailedNode: boolean,
) => {
  const isReadonly = (node.data as ConfigurationArray | ConfigurationObject | ConfigurationField).isReadonly;
  return cn(s.collapseNode, {
    [s.collapseNode_beforeFailed]: isBeforeFailedNode,
    [s.collapseNode_failed]: hasError,
    [s.collapseNode_disabled]: !hasError && isReadonly,
    [s.isSelected]: isSelected,
    [s.isExpandable]: !!node?.children?.length,
  });
};

const RequiredAtRootTree = () => {
  const ref = useRef<HTMLDivElement>(null);
  const filter: ConfigurationTreeFilter = { title: '', showAdvanced: true, showInvisible: true };
  const [treeState, setTreeState] = useState<ConfigurationTreeState>({ dragNode: null, selectedNode: null });

  const schema: SchemaDefinition = {
    $schema: 'https://json-schema.org/draft/2020-12/schema',
    title: 'Internal: required at "/" must attach to /x',
    type: 'object',
    readOnly: false,
    additionalProperties: false,
    properties: {
      x: { title: 'x', type: 'string', readOnly: false },
    },
    required: ['x'],
  };

  const configuration: JSONObject = {};
  const attributes: ConfigurationAttributes = {};

  const configNode: ConfigurationNode = buildConfigurationNodes(schema, configuration, attributes, false);
  const nodeDictionary = buildNodeDictionary(configNode);
  const viewConfigTree = buildConfigurationTree(configNode, filter, treeState);

  // Synthetic AJV-like error to demonstrate why `joinInstancePathWithSegment` exists:
  // when instancePath is "/", naive string concatenation yields "//x" and the leaf node won't show an error marker.
  const rawErrors = [
    {
      instancePath: '/',
      parentSchema: schema,
      data: configuration,
      keyword: 'required',
      message: "must have required property 'x'",
      params: { missingProperty: 'x' },
    },
  ];

  const { configurationErrors } = jsonSchemaValidationService.mapRawErrorsToConfigurationErrors(
    'ajv',
    rawErrors,
    attributes,
  );

  const handleGetNodeClassName = (node: ConfigurationNodeView) => {
    const hasError = configurationErrors[node.key] !== undefined;
    const isSelected = node.key === treeState.selectedNode?.key;
    const failedNodeInfo = getFailedNodeInfo(nodeDictionary, configurationErrors, node.data.parentNode.key || node.key);
    const isBeforeFailedNode = failedNodeInfo ? failedNodeInfo.lastFailedNodeIndex > node.index : false;
    return getNodeClassName(node, hasError, isSelected, isBeforeFailedNode);
  };

  const handleRenderNodeContent = (
    node: ConfigurationNodeView,
    isExpanded: boolean,
    onExpand: (isOpen: boolean) => void,
  ) => {
    const errors = getErrorsForTreeRow(configurationErrors, node.key);

    if (node.data.type === 'field') {
      return (
        <FieldNodeContent
          node={node}
          errors={errors}
          onClick={(n) => setTreeState({ ...treeState, selectedNode: n })}
          onClear={() => null}
          onDelete={() => null}
          onChange={() => null}
          onFieldAttributeChange={() => null}
          onDragStart={() => null}
          onDragEnd={() => null}
        />
      );
    }

    return (
      <NodeWithChildrenContent
        node={node}
        isExpanded={isExpanded}
        errors={errors}
        onClear={() => null}
        onDelete={() => null}
        onChange={() => null}
        onChangeWithAttributes={() => null}
        onExpand={onExpand}
        onFieldAttributeChange={() => null}
        onDragStart={() => null}
        onDragEnd={() => null}
      />
    );
  };

  return (
    <div style={{ padding: 12 }}>
      <div style={{ marginBottom: 8 }}>
        This story renders the tree with a synthetic AJV error (`instancePath: "/"`, `required: x`). With
        `joinInstancePathWithSegment` you should see an error marker on `/x`. If you replace it with `$
        {'${error.instancePath}/${missingProperty}'}`, the marker will disappear because the key becomes a double-slash
        path.
      </div>
      <div className={s.collapseNode__root} ref={ref}>
        <CollapseNode
          node={viewConfigTree}
          treeRef={ref}
          isInitiallyExpanded={viewConfigTree.key === rootNodeKey}
          areExpandedAll={false}
          getNodeClassName={handleGetNodeClassName}
          renderNodeContent={handleRenderNodeContent}
        />
      </div>
    </div>
  );
};

export const RequiredAtRootPathJoin = {
  render: () => <RequiredAtRootTree />,
} satisfies Story;
