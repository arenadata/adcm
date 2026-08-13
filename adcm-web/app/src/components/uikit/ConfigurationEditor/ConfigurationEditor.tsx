import { useCallback, useRef, useState } from 'react';
import ConfigurationTree from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree';
import AddConfigurationFieldDialog from '@uikit/ConfigurationEditor/Dialogs/AddConfigurationFieldDialog/AddConfigurationFieldDialog';
import EditConfigurationFieldDialog from '@uikit/ConfigurationEditor/Dialogs/EditConfigurationFieldDialog/EditConfigurationFieldDialog';
import type {
  ConfigurationField,
  ConfigurationNodePath,
  ConfigurationNodeView,
  ConfigurationSelectableObject,
  ConfigurationTreeFilter,
} from './ConfigurationEditor.types';
import {
  editField,
  addField,
  deleteField,
  addArrayItem,
  deleteArrayItem,
  moveArrayItem,
} from './ConfigurationEditor.utils';
import type { ConfigurationData, ConfigurationSchema, ConfigurationAttributes, FieldAttributes } from '@models/adcm';
import type { JSONPrimitive, JSONValue } from '@models/json';
import { DEFAULT_JSON_SCHEMA_ENGINE, type JsonSchemaEngineId } from '@utils/jsonSchema/JsonSchemaValidationService';
import {
  buildOneOfMetaAttributesSyncPayload,
  syncFieldAttributes,
} from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTreeAttributes.utils';
import type { FieldAttributesSyncPayload } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.types';
import { isInlineEditablePrimitiveField } from '@uikit/ConfigurationEditor/InlinePrimitiveFieldControl/InlinePrimitiveFieldControl.utils';
import {
  clearOneOfBranchStorePath,
  resolveOneOfSelectionValue,
  type OneOfBranchStore,
} from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.utils';
import { getValueByPath } from '@utils/objectUtils';

type SelectedNode = {
  node: ConfigurationNodeView;
  ref: React.RefObject<HTMLElement>;
};

const buildNodeKey = (path: ConfigurationNodePath) => `/${path.join('/')}`;

export interface ConfigurationEditorProps {
  schema: ConfigurationSchema;
  attributes: ConfigurationAttributes;
  configuration: ConfigurationData;
  filter: ConfigurationTreeFilter;
  areExpandedAll: boolean;
  onConfigurationChange: (configuration: ConfigurationData) => void;
  onAttributesChange: (attributes: ConfigurationAttributes) => void;
  onConfigurationAndAttributesChange: (configuration: ConfigurationData, attributes: ConfigurationAttributes) => void;
  onChangeIsValid?: (isValid: boolean) => void;
  isReadOnly?: boolean;
  validationEngine?: JsonSchemaEngineId;
}

const ConfigurationEditor = ({
  schema,
  attributes,
  configuration,
  areExpandedAll,
  filter,
  onConfigurationChange,
  onAttributesChange,
  onConfigurationAndAttributesChange,
  onChangeIsValid,
  isReadOnly = false,
  validationEngine = DEFAULT_JSON_SCHEMA_ENGINE,
}: ConfigurationEditorProps) => {
  const [dialogTarget, setDialogTarget] = useState<SelectedNode | null>(null);
  const [selectedNodeKey, setSelectedNodeKey] = useState<string | null>(null);
  const [focusNodeKey, setFocusNodeKey] = useState<string | null>(null);
  const [isEditFieldDialogOpen, setIsEditFieldDialogOpen] = useState(false);
  const [isAddFieldDialogOpen, setIsAddFieldDialogOpen] = useState(false);
  const oneOfBranchStoreRef = useRef<OneOfBranchStore>({});

  const handleFocusNodeHandled = useCallback(() => {
    setFocusNodeKey(null);
  }, []);

  const handleOpenEditFieldDialog = useCallback(
    (node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => {
      if (node.data.type === 'field' && isInlineEditablePrimitiveField((node.data as ConfigurationField).fieldSchema)) {
        return;
      }

      setSelectedNodeKey(node.key);
      setDialogTarget({ node, ref: nodeRef });
      setIsEditFieldDialogOpen(true);
    },
    [],
  );

  const handleOpenAddFieldDialog = useCallback((node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => {
    setDialogTarget({ node, ref: nodeRef });
    setIsAddFieldDialogOpen(true);
  }, []);

  const handleAddArrayItem = useCallback(
    (node: ConfigurationNodeView) => {
      const arrayValue = getValueByPath(configuration, buildNodeKey(node.data.path), '/');
      const newIndex = Array.isArray(arrayValue) ? arrayValue.length : 0;
      const newNodeKey = buildNodeKey([...node.data.path, newIndex]);
      setSelectedNodeKey(newNodeKey);
      setFocusNodeKey(newNodeKey);
      const newConfiguration = addArrayItem(configuration, node.data.path, node.data.fieldSchema);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleFieldEditorOpenChange = () => {
    setDialogTarget(null);
    setIsEditFieldDialogOpen(false);
    setIsAddFieldDialogOpen(false);
  };

  const handleValueChange = useCallback(
    (node: ConfigurationNodeView, value: JSONValue) => {
      const newConfiguration = editField(configuration, node.data.path, value);
      if (newConfiguration) {
        onConfigurationChange(newConfiguration);
      }
    },
    [configuration, onConfigurationChange],
  );

  const handleValueChangeWithAttributes = useCallback(
    (node: ConfigurationNodeView, value: JSONValue, payload: FieldAttributesSyncPayload) => {
      const nextConfiguration = editField(configuration, node.data.path, value);
      if (!nextConfiguration) return;
      const nextAttributes = syncFieldAttributes(attributes, payload);
      onConfigurationAndAttributesChange(nextConfiguration, nextAttributes);
    },
    [attributes, configuration, onConfigurationAndAttributesChange],
  );

  const handleSelectOneOfBranch = useCallback(
    (node: ConfigurationNodeView, selection: string) => {
      if (node.data.type !== 'selectableObject') {
        return;
      }

      const data = node.data as ConfigurationSelectableObject;
      const nextValue = resolveOneOfSelectionValue(
        data.value,
        selection,
        data.oneOfSchemaDefaults,
        oneOfBranchStoreRef.current,
        node.key,
      );
      const payload = buildOneOfMetaAttributesSyncPayload(data.fieldSchema, data.value, nextValue, data.path);

      handleValueChangeWithAttributes(node, nextValue, payload);
    },
    [handleValueChangeWithAttributes],
  );

  const handleAddEmptyObject = useCallback(
    (node: ConfigurationNodeView) => {
      setSelectedNodeKey(buildNodeKey(node.data.path));
      const newConfiguration = editField(configuration, node.data.path, node.data.fieldSchema.default as JSONValue);
      if (newConfiguration) {
        onConfigurationChange(newConfiguration);
      }
    },
    [configuration, onConfigurationChange],
  );

  const handleAddField = useCallback(
    (node: ConfigurationNodeView, fieldName: string, value: JSONPrimitive) => {
      const newFieldPath = [...node.data.path, fieldName];
      const newNodeKey = buildNodeKey(newFieldPath);
      setSelectedNodeKey(newNodeKey);
      setFocusNodeKey(newNodeKey);
      const newConfiguration = addField(configuration, newFieldPath, value);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleClearField = useCallback(
    (node: ConfigurationNodeView) => {
      if (node.data.type === 'selectableObject') {
        clearOneOfBranchStorePath(oneOfBranchStoreRef.current, node.key);
      }

      const newConfiguration = editField(configuration, node.data.path, null);
      if (newConfiguration) {
        onConfigurationChange(newConfiguration);
      }
    },
    [configuration, onConfigurationChange],
  );

  const handleDeleteField = useCallback(
    (node: ConfigurationNodeView) => {
      const parentNodeData = node.data.parentNode.data;

      const isParentArray = parentNodeData.type === 'array';
      const isParentObject = parentNodeData.type === 'object';

      if (node.key === selectedNodeKey) {
        setSelectedNodeKey(null);
      }

      if (node.data.type === 'selectableObject') {
        clearOneOfBranchStorePath(oneOfBranchStoreRef.current, node.key);
      }

      if (isParentArray) {
        const newConfiguration = deleteArrayItem(configuration, node.data.path);
        onConfigurationChange(newConfiguration);
      }

      if (isParentObject) {
        const newConfiguration = deleteField(configuration, node.data.path);
        onConfigurationChange(newConfiguration);
      }
    },
    [configuration, onConfigurationChange, selectedNodeKey],
  );

  const handleFieldAttributesChange = useCallback(
    (path: string, fieldAttributes: FieldAttributes) => {
      onAttributesChange({
        ...attributes,
        [path]: fieldAttributes,
      });
    },
    [attributes, onAttributesChange],
  );

  const handleMoveArrayItem = useCallback(
    (node: ConfigurationNodeView, dropPlaceHolderNode: ConfigurationNodeView) => {
      const newNodePath = dropPlaceHolderNode.data.path;
      const newConfiguration = moveArrayItem(configuration, node.data.path, newNodePath);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  return (
    <>
      <ConfigurationTree
        schema={schema}
        configuration={configuration}
        attributes={attributes}
        filter={filter}
        areExpandedAll={areExpandedAll}
        selectedNodeKey={selectedNodeKey}
        focusNodeKey={focusNodeKey}
        onFocusNodeHandled={handleFocusNodeHandled}
        onSelectNode={setSelectedNodeKey}
        validationEngine={validationEngine}
        onAddEmptyObject={handleAddEmptyObject}
        onEditField={handleOpenEditFieldDialog}
        onAddField={handleOpenAddFieldDialog}
        onMoveArrayItem={handleMoveArrayItem}
        onClear={handleClearField}
        onDelete={handleDeleteField}
        onChange={handleValueChange}
        onSelectOneOfBranch={handleSelectOneOfBranch}
        onAddArrayItem={handleAddArrayItem}
        onFieldAttributesChange={handleFieldAttributesChange}
        onChangeIsValid={onChangeIsValid}
        isReadOnly={isReadOnly}
      />
      {dialogTarget && isEditFieldDialogOpen && (
        <EditConfigurationFieldDialog
          node={dialogTarget.node}
          triggerRef={dialogTarget.ref}
          isOpen={dialogTarget !== null}
          onOpenChange={handleFieldEditorOpenChange}
          onChange={handleValueChange}
        />
      )}
      {dialogTarget && isAddFieldDialogOpen && (
        <AddConfigurationFieldDialog
          node={dialogTarget.node}
          triggerRef={dialogTarget.ref}
          isOpen={dialogTarget !== null}
          onOpenChange={handleFieldEditorOpenChange}
          onAddField={handleAddField}
        />
      )}
    </>
  );
};

export default ConfigurationEditor;
