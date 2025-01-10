import { monaco } from './MonacoCodeEditor.types';
import type {
  EditorFile,
  languages,
  SymbolsDictionary,
  ITextModel,
  IMarker,
  YamlParseError,
  ParseYamlResult,
} from './MonacoCodeEditor.types';
import yaml from 'yaml';
import type { JSONObject } from '@models/json';

import { ILanguageFeaturesService } from 'monaco-editor/esm/vs/editor/common/services/languageFeatures.js';
import type { TreeElement } from 'monaco-editor/esm/vs/editor/contrib/documentSymbols/browser/outlineModel.js';
import { OutlineModel } from 'monaco-editor/esm/vs/editor/contrib/documentSymbols/browser/outlineModel.js';
import { StandaloneServices } from 'monaco-editor/esm/vs/editor/standalone/browser/standaloneServices.js';

export const createOrUpdateModel = (file: EditorFile) => {
  const uri = monaco.Uri.parse(file.uri);
  let model = file.uri && monaco.editor.getModel(uri);

  if (model) {
    // Cannot create two models with the same URI,
    // if model with the given URI is already created, just update it.
    model.setValue(file.text);
    monaco.editor.setModelLanguage(model, file.language);
  } else {
    model = monaco.editor.createModel(file.text, file.language, uri);
  }

  return model;
};

export const jsonToYamlText = (config: JSONObject): string => {
  const yamlConfig = yaml.parse(JSON.stringify(config));
  return yaml.stringify(yamlConfig);
};

export const parseYaml = (model: ITextModel): ParseYamlResult => {
  const markers: IMarker[] = [];
  const text = model.getValue();

  try {
    const json = yaml.parse(text) as JSONObject;
    return { json };
  } catch (e) {
    const yamlParseError = e as YamlParseError;
    console.error('yaml parse error', e);

    let startPosition = { line: 0, col: 0 };
    let endPosition = startPosition;

    if (yamlParseError.linePos) {
      startPosition = yamlParseError.linePos[0];
      endPosition = yamlParseError.linePos.length === 2 ? yamlParseError.linePos[1] : yamlParseError.linePos[0];
    }

    markers.push({
      message: `${yamlParseError.code}: ${yamlParseError.message}`, // TODO: error can be customized
      severity: monaco.MarkerSeverity.Error,
      startLineNumber: startPosition.line,
      startColumn: startPosition.col,
      endLineNumber: endPosition.line,
      endColumn: endPosition.col,
      owner: 'yaml',
      resource: model.uri,
    });
  }

  return { json: null, markers };
};

export const getSymbolsDictionary = async (model: ITextModel) => {
  const result: SymbolsDictionary = {};
  const { documentSymbolProvider } = StandaloneServices.get(ILanguageFeaturesService);
  const outline = await OutlineModel.create(documentSymbolProvider, model);

  for (const { symbol, path } of iterateSymbols(outline.children, '')) {
    result[path] = symbol;
  }

  return result;
};

export const setCustomMarkers = (model: ITextModel, owner: string, markers: IMarker[]) => {
  monaco.editor.setModelMarkers(model, owner, markers);
};

export const resetCustomMarkers = (owner: string) => {
  monaco.editor.removeAllMarkers(owner);
};

export const exposeAdditionalInfo = async (model: ITextModel) => {
  const uri = model.uri.toString();

  const worker = await (await monaco.languages.json.getWorker())();
  console.info(worker);

  const doc = await worker.parseJSONDocument(uri);
  console.info(doc);

  const schema = await worker.getMatchingSchemas(uri);
  console.info(schema);

  // biome-ignore lint/suspicious/noExplicitAny:
  const textDoc = await (worker as any)._getTextDocument(uri);
  console.info(textDoc);

  const markers = monaco.editor.getModelMarkers({ resource: model.uri });
  console.info(markers);

  const decorators = model.getAllDecorations();
  console.info(decorators);
};

function* iterateSymbols(
  symbols: Map<number, TreeElement>,
  path: string,
): Iterable<{ symbol: languages.DocumentSymbol; path: string }> {
  for (const [, element] of symbols) {
    if (element.symbol === undefined) {
      continue;
    }

    const symbolPath = `${path}/${element.symbol.name}`;
    yield { symbol: element.symbol, path: symbolPath };
    if (element.children) {
      yield* iterateSymbols(element.children, symbolPath);
    }
  }
}

export const unknownSchemaToMonacoEditorSchemas = (schema: unknown, modelUri: string) => {
  if (!schema) return undefined;
  return [
    {
      uri: modelUri,
      fileMatch: [modelUri], // associate with our model
      schema,
    },
  ];
};
