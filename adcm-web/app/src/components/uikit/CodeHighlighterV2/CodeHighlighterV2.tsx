import React, { ReactNode, useMemo, useRef, useState } from 'react';
import { refractor } from 'refractor';
import { getLines, getParsedCode } from '@uikit/CodeHighlighterV2/CodeHighlighterHelperV2';
import './CodeHighlighterTemeV2.scss';
import s from './CodeHighlighterV2.module.scss';
import cn from 'classnames';
import CopyButton from '@uikit/CodeHighlighter/CopyButton/CopyButton';
import IconButton from '@uikit/IconButton/IconButton';
import ScrollBar from '@uikit/ScrollBar/ScrollBar';
import ScrollBarWrapper from '@uikit/ScrollBar/ScrollBarWrapper';

export interface CodeHighlighterV2Props {
  code: string;
  lang: string;
  isNotCopy?: boolean;
  isSecret?: boolean;
  className?: string;
  dataTestPrefix?: string;
  codeOverlay?: ReactNode;
}

const CodeHighlighterV2 = ({
  code,
  lang = 'bash',
  isNotCopy = false,
  isSecret,
  className,
  dataTestPrefix = '',
  codeOverlay,
}: CodeHighlighterV2Props) => {
  const [isSecretVisible, setIsSecretVisible] = useState(!isSecret);
  const prepCode = useMemo(() => (isSecretVisible ? code : code.replace(/./g, '*')), [code, isSecretVisible]);
  const contentRef = useRef<HTMLDivElement>(null);

  const { parsedCode, lines, patchWidth } = useMemo(() => {
    const lines = getLines(prepCode);
    const charCount = lines[lines.length - 1].toString().length;

    return {
      parsedCode: getParsedCode(refractor.highlight(prepCode, lang)),
      lines,
      patchWidth: charCount * 7.8 - 1,
    };
  }, [prepCode, lang]);

  const wrapperStyles = {
    maxHeight: '100%',
    '--code-highlite-lines-width': `${patchWidth}px`,
  };

  const toggleShowSecret = () => {
    setIsSecretVisible((prevValue) => !prevValue);
  };

  return (
    <div className={cn(className, s.codeHighlighter)} style={wrapperStyles}>
      {!isNotCopy && <CopyButton code={code} className={s.codeHighlighter__copyBtn} />}
      {isSecret && (
        <IconButton
          className={s.codeHighlighter__showSecretBtn}
          type="button"
          icon={isSecretVisible ? 'eye' : 'eye-crossed'}
          size={20}
          onClick={toggleShowSecret}
        />
      )}
      <div className={s.codeHighlighterWrapper} data-test={`${dataTestPrefix}_code-highlite`} ref={contentRef}>
        <div className={s.codeHighlighterLinesWrapper}>
          <div className={cn(s.codeHighlighterLines, s.codeHighlighterFontParams)}>
            {lines.map((lineNum) => (
              <div key={lineNum}>{lineNum}</div>
            ))}
          </div>
        </div>
        <div className={s.codeHighlighterCodeWrapper}>
          <pre className={cn('language-', s.codeHighlighterCode, s.codeHighlighterFontParams)}>{parsedCode}</pre>
          {codeOverlay && <div className={s.codeHighlighterCodeOverlay}>{codeOverlay}</div>}
        </div>
      </div>
      <ScrollBarWrapper position="right" className={s.highlighterScrollVertical}>
        <ScrollBar contentRef={contentRef} orientation="vertical" />
      </ScrollBarWrapper>
      <ScrollBarWrapper position="bottom" className={s.highlighterScrollHorizontal}>
        <ScrollBar contentRef={contentRef} orientation="horizontal" />
      </ScrollBarWrapper>
    </div>
  );
};

export default CodeHighlighterV2;
