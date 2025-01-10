import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import { Range, languages, MarkerSeverity, Emitter } from 'monaco-editor';
import type { JSONObject } from '@models/json';
import type { ReactNode } from 'react';

export type { YAMLParseError as YamlParseError } from 'yaml';

export { monaco, Range, languages, MarkerSeverity, Emitter };
export type IEvent<T> = monaco.IEvent<T>;
export type ITextModel = monaco.editor.ITextModel;
export type IMarker = monaco.editor.IMarker;
export type IPosition = monaco.IPosition;
export type Position = monaco.Position;
export type IRange = monaco.IRange;
export type IDisposable = monaco.IDisposable;
export type IStandaloneCodeEditor = monaco.editor.IStandaloneCodeEditor;
export type IIdentifiedSingleEditOperation = monaco.editor.IIdentifiedSingleEditOperation;
export type IGlyphMarginWidget = monaco.editor.IGlyphMarginWidget;
export type IEditorDecorationsCollection = monaco.editor.IEditorDecorationsCollection;
export type IModelDecorationOptions = monaco.editor.IModelDecorationOptions;
export type IModelDeltaDecoration = monaco.editor.IModelDeltaDecoration;
export type InjectedTextOptions = monaco.editor.InjectedTextOptions;
export type IEditorMouseEvent = monaco.editor.IEditorMouseEvent;
export type IPartialEditorMouseEvent = monaco.editor.IPartialEditorMouseEvent;
export type IModelContentChangedEvent = monaco.editor.IModelContentChangedEvent;
export type IMouseTarget = monaco.editor.IMouseTarget;
export type IContentWidget = monaco.editor.IContentWidget;
export type ILayoutWidget = monaco.editor.IOverlayWidget;
export type IContentWidgetPosition = monaco.editor.IContentWidgetPosition;
export const ContentWidgetPositionPreference = monaco.editor.ContentWidgetPositionPreference;
export const OverlayWidgetPositionPreference = monaco.editor.OverlayWidgetPositionPreference;

export type ValidationResult = {
  owner: string;
  markers: IMarker[];
};

export type ParseYamlResult =
  | {
      json: null;
      markers: IMarker[];
    }
  | { json: JSONObject };

export type SymbolsDictionary = { [path: string]: languages.DocumentSymbol };

export interface MonacoCodeEditorContentWidget {
  type: 'content';
  getWidget(): IContentWidget;
  renderWidget(): ReactNode;
}

export interface MonacoCodeEditorOverlayWidget {
  type: 'overlay';
  getWidget(): ILayoutWidget;
  renderWidget(): ReactNode;
}

export type MonacoCodeEditorWidget = MonacoCodeEditorContentWidget | MonacoCodeEditorOverlayWidget;

export interface EditorFile {
  uri: string;
  text: string;
  language: string;
  // biome-ignore lint/suspicious/noExplicitAny:
  schema?: any;
  validate?: boolean;
}

export interface OpenedFile {
  uri: monaco.Uri;
  model: ITextModel;
}

export type ChangeEvent = {
  value: string;
  model: ITextModel;
  event?: IModelContentChangedEvent;
};

export interface MonacoCodeEditorOptions {
  glyphMargin?: boolean;
  theme?: string;
  showMinimap?: boolean;
  isReadOnly?: boolean;
}

export type GetSuggestionsCallback = (model: ITextModel, position: IPosition) => languages.CompletionItem[];

export interface CodeEditorModel extends IDisposable {
  readonly onChange: IEvent<ChangeEvent>;
  readonly onMarkersChange: IEvent<IMarker[]>;
  readonly onDispose: IEvent<void>;
  readonly editorRef: IStandaloneCodeEditor;
  openFile: (file: EditorFile) => ITextModel;
  closeFile: () => void;
  setPosition: (position: IPosition) => void;
  updateOptions: (options: MonacoCodeEditorOptions) => void;
  registerAutocomplete: (language: string, getSuggestions: GetSuggestionsCallback) => void;
  unregisterAutocomplete: () => void;
}
