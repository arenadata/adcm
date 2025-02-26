import { useCallback, useRef, useState } from 'react';
import MonacoCodeEditor from '@uikit/MonacoCodeEditor/MonacoCodeEditor';
import type {
  MonacoCodeEditorWidget,
  IMarker,
  ITextModel,
  CodeEditorModel,
} from '@uikit/MonacoCodeEditor/MonacoCodeEditor.types';
import {
  parseYaml,
  jsonToYamlText,
  getSymbolsDictionary,
  setCustomMarkers,
} from '@uikit/MonacoCodeEditor/MonacoCodeEditor.utils';
import { validate } from '@uikit/ConfigurationEditor/ConfigurationTree/ConfigurationTree.utils';
import { getAdcmErrorMarkers, getCommentsAppends, getSymbolsDictionaryWithSchema } from './AdcmConfigEditor.utils';

import type { ConfigurationAttributes, FieldAttributes, SchemaDefinition } from '@models/adcm';
import type { JSONObject } from '@models/json';

import type { AdcmFieldAttributesDecoratorClickEventDetails } from './AdcmFieldAttributesDecoratorsController';
import { AdcmFieldAttributesDecoratorsController } from './AdcmFieldAttributesDecoratorsController';
import AdcmFieldAttributesProvider from './AdcmFieldAttributesWidget/AdcmFieldAttributesProvider';
import { AdcmFieldAttributesWidget } from './AdcmFieldAttributesWidget/AdcmFieldAttributesWidget';

import MarkersWidgetProvider from '../MarkersWidget/MarkersWidgetProvider';
import { MarkersWidget } from '../MarkersWidget/MarkersWidget';

export interface AdcmConfigEditorProps {
  attributes: ConfigurationAttributes;
  schema: SchemaDefinition;
  config: JSONObject;
  autoApplyComments?: boolean;
}

const AdcmConfigEditor = ({ schema, config, attributes, autoApplyComments = false }: AdcmConfigEditorProps) => {
  const editorModelRef = useRef<CodeEditorModel | null>(null);
  const localConfig = useRef<JSONObject>(config);
  const localText = useRef(jsonToYamlText(config));

  const localAttributes = useRef(attributes);

  const [markers, setMarkers] = useState<IMarker[]>([]);
  const [editFieldAttributesProps, setEditFieldAttributesProps] = useState<{
    model: ITextModel | null;
    path: string;
    attributes: FieldAttributes;
  }>({
    model: null,
    path: '',
    attributes: { isActive: true, isSynchronized: false },
  });
  const fieldAttributesWidget = useRef(new AdcmFieldAttributesWidget());
  const markersWidget = useRef(new MarkersWidget());
  const widgetsRef = useRef<MonacoCodeEditorWidget[]>([fieldAttributesWidget.current, markersWidget.current]);

  const decoratorsController = useRef<AdcmFieldAttributesDecoratorsController | null>(null);

  const handleWidgetClick = (event: Event) => {
    const detail = (event as CustomEvent<AdcmFieldAttributesDecoratorClickEventDetails>).detail;
    console.info(detail);
    fieldAttributesWidget.current.showWidget(detail.attributes, detail.position);
    setEditFieldAttributesProps({
      model: detail.model,
      path: detail.path,
      attributes: detail.attributes,
    });
  };

  const handleMount = async (editorModel: CodeEditorModel) => {
    editorModelRef.current = editorModel;
    const editor = editorModel.editorRef;

    decoratorsController.current = new AdcmFieldAttributesDecoratorsController(editor);
    decoratorsController.current.addEventListener('click', handleWidgetClick);

    fieldAttributesWidget.current.init(editor);
    markersWidget.current.init(editor);
    markersWidget.current.showWidget();

    if (autoApplyComments) {
      const model = editor.getModel();
      if (model) {
        const symbolsDictionary = await getSymbolsDictionary(model);
        const nodesDictionary = getSymbolsDictionaryWithSchema(schema, localConfig.current, localAttributes.current);
        const comments = getCommentsAppends(symbolsDictionary, nodesDictionary);
        model.applyEdits(comments);
      }
    }
  };

  const handleUnmount = () => {
    fieldAttributesWidget.current.hideWidget();
    markersWidget.current.hideWidget();
    decoratorsController.current?.removeEventListener('click', handleWidgetClick);
    decoratorsController.current?.dispose();
  };

  const handleFieldAttributesChange = useCallback(
    async (path: string, fieldAttributes: FieldAttributes) => {
      localAttributes.current = { ...localAttributes.current, [path]: fieldAttributes };
      fieldAttributesWidget.current.hideWidget();

      const model = editFieldAttributesProps.model; // editorRef.current?.getModel();
      if (model) {
        const symbolsDictionary = await getSymbolsDictionary(model);
        const adcmSchemaValidationResult = validate(schema, localConfig.current, localAttributes.current);
        const markers = getAdcmErrorMarkers(model, adcmSchemaValidationResult.configurationErrors, symbolsDictionary);
        setCustomMarkers(model, 'adcm', markers);

        const nodesDictionary = getSymbolsDictionaryWithSchema(schema, localConfig.current, localAttributes.current);
        decoratorsController.current?.decorate(localAttributes.current, symbolsDictionary, nodesDictionary);
      }
    },
    [schema, editFieldAttributesProps.model],
  );

  const handleFieldAttributeCancel = () => {
    fieldAttributesWidget.current.hideWidget();
  };

  const handleChange = useCallback(
    async (_value: string, model: ITextModel) => {
      // parse
      const parseResult = parseYaml(model);
      if (parseResult.json !== null) {
        localConfig.current = parseResult.json as JSONObject;
        const symbolsDictionary = await getSymbolsDictionary(model);

        // validate
        const adcmSchemaValidationResult = validate(schema, localConfig.current, localAttributes.current);
        const markers = getAdcmErrorMarkers(model, adcmSchemaValidationResult.configurationErrors, symbolsDictionary);
        setCustomMarkers(model, 'adcm', markers);

        const nodesDictionary = getSymbolsDictionaryWithSchema(schema, localConfig.current, localAttributes.current);

        // decorate
        decoratorsController.current?.decorate(localAttributes.current, symbolsDictionary, nodesDictionary);

        // todo: add collapse nodes
      } else {
        setCustomMarkers(model, 'adcm', parseResult.markers);
      }
    },
    [schema],
  );

  const handleMarkerClick = (marker: IMarker) => {
    editorModelRef.current?.setPosition({ lineNumber: marker.startLineNumber, column: marker.startColumn });
  };

  return (
    <MarkersWidgetProvider markers={markers} onClick={handleMarkerClick}>
      <AdcmFieldAttributesProvider
        path={editFieldAttributesProps.path}
        attributes={editFieldAttributesProps.attributes}
        onCancel={handleFieldAttributeCancel}
        onFieldAttributesChange={handleFieldAttributesChange}
      >
        <MonacoCodeEditor
          uri="http://myserver/adcm-config.json"
          language="yaml"
          text={localText.current}
          validate={false}
          widgets={widgetsRef.current}
          onChange={handleChange}
          onMount={handleMount}
          onUnmount={handleUnmount}
          onMarkersChange={setMarkers}
        />
      </AdcmFieldAttributesProvider>
    </MarkersWidgetProvider>
  );
};

export default AdcmConfigEditor;
