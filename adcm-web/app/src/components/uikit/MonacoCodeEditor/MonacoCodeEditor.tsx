import { useRef, useEffect, useState, useCallback } from 'react';
import { MonacoCodeEditorModel } from './MonacoCodeEditorModel';
import type {
  languages,
  MonacoCodeEditorOptions,
  IDisposable,
  IMarker,
  MonacoCodeEditorWidget,
  IPosition,
  IStandaloneCodeEditor,
  CodeEditorModel,
  ChangeEvent,
  ITextModel,
  IModelContentChangedEvent,
} from './MonacoCodeEditor.types';
import './MonacoCodeEditor.workers';
import s from './MonacoCodeEditor.module.scss';
import MonacoCodeEditorProblems from './MonacoCodeEditorProblems/MonacoCodeEditorProblems';
import MonacoCodeEditorWidgets from './MonacoCodeEditorWidgets';

export interface MonacoCodeEditorProps {
  uri: string;
  language: string;
  text: string;
  // biome-ignore lint/suspicious/noExplicitAny:
  schema?: any;
  validate?: boolean;
  options?: MonacoCodeEditorOptions;
  widgets?: MonacoCodeEditorWidget[];
  onChange?: (value: string, model: ITextModel, event?: IModelContentChangedEvent) => void;
  onMarkersChange?: (markers: IMarker[]) => void;
  onAutoComplete?: (model: ITextModel, position: IPosition) => languages.CompletionItem[];
  onMount?: (editorModel: CodeEditorModel) => void;
  onUnmount?: (editor: IStandaloneCodeEditor) => void;
}

const defaultOptions: MonacoCodeEditorOptions = {
  glyphMargin: undefined,
  theme: 'vs-dark',
  showMinimap: true,
  isReadOnly: false,
};

const MonacoCodeEditor = ({
  uri,
  language,
  text,
  schema,
  validate,
  options = defaultOptions,
  widgets,
  onChange,
  onAutoComplete,
  onMount,
  onUnmount,
  onMarkersChange,
}: MonacoCodeEditorProps) => {
  const editorModelRef = useRef<CodeEditorModel | null>();
  const editorRef = useRef<IStandaloneCodeEditor | null>();
  const containerRef = useRef(null);
  const callbacks = useRef({ onChange, onMarkersChange, onAutoComplete });

  callbacks.current.onChange = onChange;
  callbacks.current.onMarkersChange = onMarkersChange;
  callbacks.current.onAutoComplete = onAutoComplete;

  const [markers, setMarkers] = useState<IMarker[]>([]);

  useEffect(() => {
    if (editorModelRef.current) {
      const file = {
        uri,
        text,
        language,
        schema,
        validate,
      };
      editorModelRef.current.openFile(file);
    }
  }, [uri, text, language, schema, validate]);

  const handleAutocomplete = useCallback((model: ITextModel, position: IPosition) => {
    return callbacks.current.onAutoComplete?.(model, position) ?? [];
  }, []);

  useEffect(() => {
    if (editorModelRef.current) {
      editorModelRef.current.unregisterAutocomplete();
      editorModelRef.current.registerAutocomplete(language, handleAutocomplete);
    }
  }, [language, handleAutocomplete]);

  useEffect(() => {
    if (containerRef.current) {
      const disposables: IDisposable[] = [];

      editorModelRef.current = new MonacoCodeEditorModel(containerRef.current);

      disposables.push(
        editorModelRef.current.onChange(({ value, model, event }: ChangeEvent) => {
          callbacks.current.onChange?.(value, model, event);
        }),
      );

      disposables.push(
        editorModelRef.current.onMarkersChange((markers: IMarker[]) => {
          setMarkers(markers);
          callbacks.current.onMarkersChange?.(markers);
        }),
      );

      disposables.push(
        editorModelRef.current.onDispose(() => {
          onUnmount?.(editorRef.current!);
          disposables.forEach((d) => d.dispose());
        }),
      );

      if (onAutoComplete) {
        editorModelRef.current.registerAutocomplete(language, handleAutocomplete);
      }

      const file = { uri, text, language, schema, validate };
      editorModelRef.current.openFile(file);
      onMount?.(editorModelRef.current);
    }

    return () => {
      editorModelRef.current?.dispose();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!editorModelRef.current) return;
    editorModelRef.current.updateOptions(options);
  }, [options]);

  const handleProblemClick = (position: IPosition) => {
    editorModelRef.current?.setPosition(position);
  };

  return (
    <div className={s.editorWrapper}>
      <div className={s.editor} ref={containerRef} />
      <MonacoCodeEditorProblems markers={markers} onProblemClick={handleProblemClick} />
      <MonacoCodeEditorWidgets widgets={widgets} />
    </div>
  );
};

export default MonacoCodeEditor;
