import { type ReactNode, type RefObject, useMemo, useState, useRef } from 'react';
import { refractor } from 'refractor';
import { useVirtualizer } from '@tanstack/react-virtual';
import { getParsedCode } from '@uikit/CodeHighlighter/CodeHighlighterHelper';
import './CodeHighlighterTheme.scss';
import s from './CodeHighlighter.module.scss';
import cn from 'classnames';
import CopyButton from '@uikit/CodeHighlighter/SubComponents/CopyButton/CopyButton';
import Button from '@uikit/Button/Button';
import SyncScroll from '@uikit/SyncScroll/SyncScroll';
import ScrollPane from '@uikit/SyncScroll/ScrollPane';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import { useFullscreen } from '@hooks/useFullscreen';
import { useFullscreenContext } from './SubComponents/FullscreenContainer/FullscreenContainer';

const virtualizerOverscan = 5;
const virtualizerEstimateSize = 20;
const patchPadding = 32;

export interface CodeHighlighterProps {
  code: string;
  language: string;
  isNotCopy?: boolean;
  isSecret?: boolean;
  className?: string;
  dataTestPrefix?: string;
  codeOverlay?: ReactNode;
  contentRef?: RefObject<HTMLDivElement>;
}

const CodeHighlighter = ({
  code,
  language = 'bash',
  isNotCopy = false,
  isSecret,
  className,
  dataTestPrefix = '',
  codeOverlay,
  contentRef: externalContentRef,
}: CodeHighlighterProps) => {
  const [isSecretVisible, setIsSecretVisible] = useState(!isSecret);
  const prepCode = useMemo(() => (isSecretVisible ? code : code.replace(/./g, '*')), [code, isSecretVisible]);

  const containerRef = useRef<HTMLDivElement>(null);
  const { isFullscreen: localIsFullScreen, toggleFullscreen } = useFullscreen(containerRef);

  const parentFullscreenContext = useFullscreenContext();

  const isFullscreen = parentFullscreenContext?.isFullscreen ?? localIsFullScreen;

  const { parsedCodeLines, lines, patchWidth } = useMemo(() => {
    const codeLines = prepCode.split(/[\r\n]/);
    const lines = codeLines.map((_, id) => id + 1);
    const charCount = lines.length.toString().length;

    const parsedCodeLines = codeLines.map((line) => {
      try {
        const highlighted = refractor.highlight(line, language);
        return getParsedCode(highlighted);
      } catch (_error) {
        return [line];
      }
    });

    return {
      parsedCodeLines,
      lines,
      patchWidth: charCount * 7.8 + patchPadding,
    };
  }, [prepCode, language]);

  const internalContentRef = useRef<HTMLDivElement>(null);
  const contentRef = externalContentRef || internalContentRef;

  const codeVirtualizer = useVirtualizer({
    count: lines.length,
    getScrollElement: () => contentRef.current,
    estimateSize: () => virtualizerEstimateSize,
    overscan: virtualizerOverscan,
  });

  const toggleShowSecret = () => {
    setIsSecretVisible((prevValue) => !prevValue);
  };

  const handleExpandBtnClick = () =>
    parentFullscreenContext ? parentFullscreenContext.toggleFullscreen() : toggleFullscreen();

  const items = codeVirtualizer.getVirtualItems();

  return (
    <div
      ref={containerRef}
      className={cn(s.codeHighlighter, className, {
        [s.codeHighlighter_expanded]: isFullscreen,
      })}
    >
      <div className={s.codeHighlighter__actions}>
        <FlexGroup gap="4px">
          {!isFullscreen && (
            <Button
              iconLeft="g2-expand"
              variant="tertiary"
              tooltipProps={{ placement: 'left' }}
              title="Full screen"
              onClick={handleExpandBtnClick}
              className={s.codeHighlighter__expandBtn}
            />
          )}
          {!isNotCopy && <CopyButton code={code} className={s.codeHighlighter__copyBtn} />}
          {isSecret && (
            <Button
              variant="tertiary"
              iconLeft={isSecretVisible ? 'eye' : 'eye-crossed'}
              onClick={toggleShowSecret}
              className={s.codeHighlighter__secretBtn}
            />
          )}
        </FlexGroup>
      </div>
      <SyncScroll>
        <div className={s.codeHighlighterWrapper} data-test={`${dataTestPrefix}_code-highlight`}>
          <ScrollPane hideScrollBars={true} syncHorizontal={false}>
            <div
              className={cn(s.codeHighlighterLines, s.codeHighlighterFontParams)}
              style={{ width: `${patchWidth}px` }}
            >
              <div className={s.virtualContainer} style={{ height: `${codeVirtualizer.getTotalSize()}px` }}>
                {items.map((virtualRow) => (
                  <div
                    key={virtualRow.key}
                    className={s.virtualLineNumber}
                    style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                  >
                    {lines[virtualRow.index]}
                  </div>
                ))}
              </div>
            </div>
          </ScrollPane>
          <ScrollPane ref={contentRef}>
            <div className={cn(s.codeHighlighterCode, s.codeHighlighterFontParams)}>
              <div className={s.virtualContainer} style={{ height: `${codeVirtualizer.getTotalSize()}px` }}>
                {items.map((virtualRow) => {
                  const lineIndex = virtualRow.index;
                  const lineContent = parsedCodeLines[lineIndex];

                  return (
                    <div
                      key={virtualRow.key}
                      className={s.virtualCodeLine}
                      style={{ height: `${virtualRow.size}px`, transform: `translateY(${virtualRow.start}px)` }}
                    >
                      <pre className="language-">{lineContent}</pre>
                    </div>
                  );
                })}
              </div>
              {codeOverlay && <div className={s.codeHighlighterCodeOverlay}>{codeOverlay}</div>}
            </div>
          </ScrollPane>
        </div>
      </SyncScroll>
    </div>
  );
};

export default CodeHighlighter;
