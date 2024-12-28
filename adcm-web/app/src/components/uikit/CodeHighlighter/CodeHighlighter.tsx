import { type ReactNode, type RefObject, useMemo, useState } from 'react';
import { refractor } from 'refractor';
import { getLines, getParsedCode } from '@uikit/CodeHighlighter/CodeHighlighterHelper';
import './CodeHighlighterTheme.scss';
import s from './CodeHighlighter.module.scss';
import cn from 'classnames';
import CopyButton from '@uikit/CodeHighlighter/SubComponents/CopyButton/CopyButton';
import IconButton from '@uikit/IconButton/IconButton';
import SyncScroll from '@uikit/SyncScroll/SyncScroll';
import ScrollPane from '@uikit/SyncScroll/ScrollPane';

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
  contentRef,
}: CodeHighlighterProps) => {
  const [isSecretVisible, setIsSecretVisible] = useState(!isSecret);
  const prepCode = useMemo(() => (isSecretVisible ? code : code.replace(/./g, '*')), [code, isSecretVisible]);

  const { parsedCode, lines, patchWidth } = useMemo(() => {
    const lines = getLines(prepCode);
    const charCount = lines[lines.length - 1].toString().length;

    return {
      parsedCode: getParsedCode(refractor.highlight(prepCode, language)),
      lines,
      patchWidth: charCount * 7.8 - 1,
    };
  }, [prepCode, language]);

  const wrapperStyles = {
    animation: 'none',
    '--code-highlight-lines-width': `${patchWidth}px`,
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
      <SyncScroll>
        <div className={s.codeHighlighterWrapper} data-test={`${dataTestPrefix}_code-highlight`}>
          <ScrollPane hideScrollBars={true} syncHorizontal={false}>
            <div className={cn(s.codeHighlighterLines, s.codeHighlighterFontParams)}>
              {lines.map((lineNum) => (
                <div key={lineNum}>{lineNum}</div>
              ))}
            </div>
          </ScrollPane>
          <ScrollPane ref={contentRef}>
            <div className={cn(s.codeHighlighterCode, s.codeHighlighterFontParams)}>
              <pre className="language-">{parsedCode}</pre>
              {codeOverlay && <div className={s.codeHighlighterCodeOverlay}>{codeOverlay}</div>}
            </div>
          </ScrollPane>
        </div>
      </SyncScroll>
    </div>
  );
};

export default CodeHighlighter;
