import { type ReactNode, type RefObject, useMemo, useState, useRef, useEffect } from 'react';
import { monaco } from '@uikit/MonacoCodeEditor/MonacoCodeEditor.types';
import { scrollEditorToEnd } from '@uikit/MonacoCodeEditor/MonacoCodeEditor.utils';
import s from './MonacoCodeViewer.module.scss';
import cn from 'classnames';
import CopyButton from '@uikit/CodeHighlighter/SubComponents/CopyButton/CopyButton';
import Button from '@uikit/Button/Button';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import { useFullscreen } from '@hooks/useFullscreen';
import '@uikit/MonacoCodeEditor/MonacoCodeEditor.workers';
import { useFullscreenContext } from '@uikit/CodeHighlighter/SubComponents/FullscreenContainer/FullscreenContainer.tsx';

export interface CodeHighlighterProps {
  code: string;
  language: string;
  isNotCopy?: boolean;
  isSecret?: boolean;
  scrollToEnd?: boolean;
  className?: string;
  dataTestPrefix?: string;
  codeOverlay?: ReactNode;
  contentRef?: RefObject<HTMLDivElement>;
}

const getTheme = () => (document.body.classList.contains('theme-dark') ? 'vs-dark' : 'vs');

const MonacoCodeViewer = ({
  code,
  language = 'bash',
  isNotCopy = false,
  isSecret,
  scrollToEnd = false,
  className,
  dataTestPrefix = '',
}: CodeHighlighterProps) => {
  const [isSecretVisible, setIsSecretVisible] = useState(!isSecret);
  const prepCode = useMemo(() => (isSecretVisible ? code : code.replace(/./g, '*')), [code, isSecretVisible]);

  const containerRef = useRef<HTMLDivElement>(null);
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const editorContainerRef = useRef<HTMLDivElement>(null);
  const { isFullscreen: localIsFullScreen, toggleFullscreen } = useFullscreen(containerRef);

  const parentFullscreenContext = useFullscreenContext();
  const isFullscreen = parentFullscreenContext?.isFullscreen ?? localIsFullScreen;

  useEffect(() => {
    if (!editorContainerRef.current) return;

    editorRef.current = monaco.editor.create(editorContainerRef.current, {
      value: prepCode,
      language,
      readOnly: true,
      theme: getTheme(),
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      wordWrap: 'off',
      fontSize: 14,
      fontFamily: "'JetBrains Mono', monospace",
      lineHeight: 20,
      automaticLayout: true,
      renderWhitespace: 'none',
      glyphMargin: false,
      occurrencesHighlight: 'off',
      selectionHighlight: false,
      padding: { top: 16, bottom: 16 },
    });

    const updateTheme = () => editorRef.current?.updateOptions({ theme: getTheme() });

    const observer = new MutationObserver(updateTheme);
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    const scrollCleanup = scrollToEnd && editorRef.current ? scrollEditorToEnd(editorRef.current) : undefined;

    return () => {
      scrollCleanup?.();
      observer.disconnect();
      editorRef.current?.dispose();
    };
  }, [prepCode, language, scrollToEnd]);

  const toggleShowSecret = () => {
    setIsSecretVisible((prevValue) => !prevValue);
  };

  const handleExpandBtnClick = () =>
    parentFullscreenContext ? parentFullscreenContext.toggleFullscreen() : toggleFullscreen();

  return (
    <div
      ref={containerRef}
      className={cn(s.monacoEditor, className, {
        [s.monacoEditor_expanded]: isFullscreen,
      })}
    >
      <div className={s.monacoEditor__actions}>
        <FlexGroup gap="4px">
          {!isFullscreen && (
            <Button
              iconLeft="g2-expand"
              variant="tertiary"
              tooltipProps={{ placement: 'left' }}
              title="Full screen"
              onClick={handleExpandBtnClick}
              className={s.monacoEditor__expandBtn}
            />
          )}
          {!isNotCopy && <CopyButton code={code} className={s.monacoEditor__copyBtn} />}
          {isSecret && (
            <Button
              variant="tertiary"
              iconLeft={isSecretVisible ? 'eye' : 'eye-crossed'}
              onClick={toggleShowSecret}
              className={s.monacoEditor__secretBtn}
            />
          )}
        </FlexGroup>
      </div>
      <div className={s.monacoEditorWrapper} data-test={`${dataTestPrefix}_monaco-editor`}>
        <div ref={editorContainerRef} className={s.monacoEditorEntity} />
      </div>
    </div>
  );
};

export default MonacoCodeViewer;
