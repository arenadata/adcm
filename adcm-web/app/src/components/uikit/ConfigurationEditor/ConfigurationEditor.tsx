import { useCallback, useState } from 'react';
import ConfigurationTree from './ConfigurationTree/ConfigurationTree';
import AddConfigurationFieldDialog from './Dialogs/AddConfigurationFieldDialog/AddConfigurationFieldDialog';
import EditConfigurationFieldDialog from './Dialogs/EditConfigurationFieldDialog/EditConfigurationFieldDialog';
import { ConfigurationNodeView, ConfigurationTreeFilter } from './ConfigurationEditor.types';
import { editField, addField, deleteField, addArrayItem, deleteArrayItem } from './ConfigurationEditor.utils';
import { ConfigurationData, ConfigurationSchema, ConfigurationAttributes, FieldAttributes } from '@models/adcm';
import { JSONPrimitive, JSONValue } from '@models/json';

type SelectedNode = {
  node: ConfigurationNodeView;
  ref: React.RefObject<HTMLElement>;
};

export interface ConfigurationEditorProps {
  schema: ConfigurationSchema;
  attributes: ConfigurationAttributes;
  configuration: ConfigurationData;
  filter: ConfigurationTreeFilter;
  areExpandedAll: boolean;
  onConfigurationChange: (configuration: ConfigurationData) => void;
  onAttributesChange: (attributes: ConfigurationAttributes) => void;
  onChangeIsValid?: (isValid: boolean) => void;
}

const ConfigurationEditor = ({
  schema,
  attributes,
  configuration,
  areExpandedAll,
  filter,
  onConfigurationChange,
  onAttributesChange,
  onChangeIsValid,
}: ConfigurationEditorProps) => {
  const [selectedNode, setSelectedNode] = useState<SelectedNode | null>(null);
  const [isEditFieldDialogOpen, setIsEditFieldDialogOpen] = useState(false);
  const [isAddFieldDialogOpen, setIsAddFieldDialogOpen] = useState(false);

  const handleOpenEditFieldDialog = useCallback(
    (node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => {
      setSelectedNode({ node, ref: nodeRef });
      setIsEditFieldDialogOpen(true);
    },
    [],
  );

  const handleOpenAddFieldDialog = useCallback((node: ConfigurationNodeView, nodeRef: React.RefObject<HTMLElement>) => {
    setSelectedNode({ node, ref: nodeRef });
    setIsAddFieldDialogOpen(true);
  }, []);

  const handleAddArrayItem = useCallback(
    (node: ConfigurationNodeView) => {
      const newConfiguration = addArrayItem(configuration, node.data.path, node.data.fieldSchema);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleFieldEditorOpenChange = () => {
    setSelectedNode(null);
    setIsEditFieldDialogOpen(false);
    setIsAddFieldDialogOpen(false);
  };

  const handleValueChange = useCallback(
    (node: ConfigurationNodeView, value: JSONPrimitive) => {
      const newConfiguration = editField(configuration, node.data.path, value);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleAddEmptyObject = useCallback(
    (node: ConfigurationNodeView) => {
      const newConfiguration = editField(configuration, node.data.path, node.data.fieldSchema.default as JSONValue);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleAddField = useCallback(
    (node: ConfigurationNodeView, fieldName: string, value: JSONPrimitive) => {
      const newFieldPath = [...node.data.path, fieldName];
      const newConfiguration = addField(configuration, newFieldPath, value);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleClearField = useCallback(
    (node: ConfigurationNodeView) => {
      const newConfiguration = editField(configuration, node.data.path, null);
      onConfigurationChange(newConfiguration);
    },
    [configuration, onConfigurationChange],
  );

  const handleDeleteField = useCallback(
    (node: ConfigurationNodeView) => {
      const parentNodeData = node.data.parentNode.data;

      const isParentArray = parentNodeData.type === 'array';
      const isParentObject = parentNodeData.type === 'object';

      if (isParentArray) {
        const newConfiguration = deleteArrayItem(configuration, node.data.path);
        onConfigurationChange(newConfiguration);
      }

      if (isParentObject) {
        const newConfiguration = deleteField(configuration, node.data.path);
        onConfigurationChange(newConfiguration);
      }
    },
    [configuration, onConfigurationChange],
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

  return (
    <>
      <ConfigurationTree
        schema={schema}
        configuration={configuration}
        attributes={attributes}
        filter={filter}
        areExpandedAll={areExpandedAll}
        onAddEmptyObject={handleAddEmptyObject}
        onEditField={handleOpenEditFieldDialog}
        onAddField={handleOpenAddFieldDialog}
        onClear={handleClearField}
        onDelete={handleDeleteField}
        onAddArrayItem={handleAddArrayItem}
        onFieldAttributesChange={handleFieldAttributesChange}
        onChangeIsValid={onChangeIsValid}
      />
      {selectedNode && isEditFieldDialogOpen && (
        <EditConfigurationFieldDialog
          node={selectedNode.node}
          triggerRef={selectedNode.ref}
          isOpen={selectedNode !== null}
          onOpenChange={handleFieldEditorOpenChange}
          onChange={handleValueChange}
        />
      )}
      {selectedNode && isAddFieldDialogOpen && (
        <AddConfigurationFieldDialog
          node={selectedNode.node}
          triggerRef={selectedNode.ref}
          isOpen={selectedNode !== null}
          onOpenChange={handleFieldEditorOpenChange}
          onAddField={handleAddField}
        />
      )}
    </>
  );
};

export default ConfigurationEditor;
