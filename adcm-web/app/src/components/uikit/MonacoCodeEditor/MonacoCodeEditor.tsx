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
import { useFullscreen } from '@hooks/useFullscreen';
import { useFullscreenContext } from '@uikit/CodeHighlighter/SubComponents/FullscreenContainer/FullscreenContainer';
import cn from 'classnames';
import MonacoCodeEditorToolbar from './MonacoCodeEditorToolbar/MonacoCodeEditorToolbar';

import { scrollEditorToEnd } from './MonacoCodeEditor.utils';

const getThemeFromDocument = () => (document.body.classList.contains('theme-dark') ? 'vs-dark' : 'vs');

export interface MonacoCodeEditorProps {
  uri: string;
  language: string;
  text: string;
  schema?: unknown;
  validate?: boolean;
  options?: MonacoCodeEditorOptions;
  widgets?: MonacoCodeEditorWidget[];
  /** When true, the editor scrolls to the last line on first load and whenever text changes (e.g. for log viewers). */
  scrollToEnd?: boolean;
  showCopyButton?: boolean;
  showFullscreenButton?: boolean;
  onChange?: (value: string, model: ITextModel, event?: IModelContentChangedEvent) => void;
  onMarkersChange?: (markers: IMarker[]) => void;
  onAutoComplete?: (model: ITextModel, position: IPosition) => languages.CompletionItem[];
  onMount?: (editorModel: CodeEditorModel) => void;
  onUnmount?: (editor: IStandaloneCodeEditor) => void;
}

const defaultOptions: MonacoCodeEditorOptions = {
  glyphMargin: false,
  theme: 'vs-dark',
  minimap: { enabled: true },
  readOnly: false,
  padding: { top: 16, bottom: 16 },
};

const MonacoCodeEditor = ({
  uri,
  language,
  text,
  schema,
  validate,
  options = defaultOptions,
  widgets,
  scrollToEnd = false,
  showCopyButton = false,
  showFullscreenButton = false,
  onChange,
  onAutoComplete,
  onMount,
  onUnmount,
  onMarkersChange,
}: MonacoCodeEditorProps) => {
  const editorModelRef = useRef<CodeEditorModel | null>();
  const editorRef = useRef<IStandaloneCodeEditor | null>();
  const containerRef = useRef<HTMLDivElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const callbacks = useRef({ onChange, onMarkersChange, onAutoComplete });

  const hasToolbar = showCopyButton || showFullscreenButton;
  const { isFullscreen, toggleFullscreen } = useFullscreen(wrapperRef);
  const parentFullscreenContext = useFullscreenContext();
  const isFullscreenActive = parentFullscreenContext?.isFullscreen ?? isFullscreen;
  const handleExpandClick = () =>
    parentFullscreenContext ? parentFullscreenContext.toggleFullscreen() : toggleFullscreen();

  callbacks.current.onChange = onChange;
  callbacks.current.onMarkersChange = onMarkersChange;
  callbacks.current.onAutoComplete = onAutoComplete;

  const [markers, setMarkers] = useState<IMarker[]>([]);
  const [theme, setTheme] = useState(() => getThemeFromDocument());

  useEffect(() => {
    if (!editorModelRef.current) return;
    const file = {
      uri,
      text,
      language,
      schema,
      validate,
    };
    editorModelRef.current.openFile(file);
    const scrollCleanup = scrollToEnd ? scrollEditorToEnd(editorModelRef.current.editorRef) : undefined;
    return () => scrollCleanup?.();
  }, [uri, text, language, schema, validate, scrollToEnd]);

  useEffect(() => {
    const observer = new MutationObserver(() => setTheme(getThemeFromDocument()));
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

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
      return () => {
        editorModelRef.current?.dispose();
        editorModelRef.current = null;
      };
    }
  }, []);

  useEffect(() => {
    if (!editorModelRef.current) return;
    editorModelRef.current.updateOptions({ ...defaultOptions, ...options, theme });
  }, [options, theme]);

  useEffect(() => {
    if (!isFullscreenActive || !editorModelRef.current || !containerRef.current) return;
    const container = containerRef.current;
    const editor = editorModelRef.current.editorRef;
    const ro = new ResizeObserver(() => editor.layout());
    ro.observe(container);
    return () => ro.disconnect();
  }, [isFullscreenActive]);

  const handleProblemClick = (position: IPosition) => {
    editorModelRef.current?.setPosition(position);
  };

  return (
    <div
      ref={wrapperRef}
      className={cn(s.editorWrapper, {
        [s.editorWrapper_withToolbar]: hasToolbar,
        [s.editorWrapper_expanded]: hasToolbar && isFullscreenActive,
      })}
    >
      {hasToolbar && (
        <MonacoCodeEditorToolbar
          className={s.editorWrapper__toolbar}
          code={text}
          showCopyButton={showCopyButton}
          showFullscreenButton={showFullscreenButton}
          isFullscreenActive={isFullscreenActive}
          onExpandClick={handleExpandClick}
        />
      )}
      <div className={s.editor} ref={containerRef} />
      <MonacoCodeEditorProblems markers={markers} onProblemClick={handleProblemClick} />
      <MonacoCodeEditorWidgets widgets={widgets} />
    </div>
  );
};

export default MonacoCodeEditor;
