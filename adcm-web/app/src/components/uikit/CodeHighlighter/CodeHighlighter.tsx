import React, { useState, useMemo } from 'react';
import cn from 'classnames';
import s from './CodeHighlighter.module.scss';
import './Themes/CodeHighlighter.module.themes.scss';
// TODO: change on https://www.npmjs.com/package/refractor
import SyntaxHighlighter from 'react-syntax-highlighter/dist/esm/default-highlight';
import customTheme from './Themes/customTheme';
import CopyButton from './CopyButton/CopyButton';
import IconButton from '@uikit/IconButton/IconButton';

type LinesWrapperProps = {
  children: React.ReactNode;
  subComponent?: React.ReactElement;
  dataTest?: string;
};

interface DefaultCodeTagProps extends React.PropsWithChildren {
  children: [boolean, React.ReactNode[]];
  linesWrapper?: React.ReactElement;
  dataTest?: string;
}

type LineNumbersProps = {
  lineCount: number;
};

export const LinesWrapper = ({ children, subComponent, dataTest }: LinesWrapperProps) => {
  return (
    <div className={cn(s['code-wrapper__code-lines'])} data-test={dataTest}>
      {children}
      {subComponent}
    </div>
  );
};

export const LineNumbers = ({ lineCount }: LineNumbersProps) => (
  <div className={cn(s['code-wrapper__line-numbers-wrapper'])}>
    {[...Array(lineCount)].map((item: unknown, id) => (
      <div key={id}>{id + 1}</div>
    ))}
  </div>
);

const DefaultCodeTag = ({ children }: DefaultCodeTagProps) => {
  const [, childArray] = children;

  return (
    <div className={cn(s['code-wrapper'])}>
      <LineNumbers lineCount={React.Children.count(childArray)} />
      <LinesWrapper dataTest="code-wrapper-log-text">{childArray}</LinesWrapper>
    </div>
  );
};

const CodePre = ({ children }: React.PropsWithChildren) => (
  <div className={cn(s['code-pre'], s['highlighter_font-params'])}>{children}</div>
);

const SyntaxFallback: React.FC<{ text: string }> = ({ text }) => {
  const lineCount = text.split('\n').length;
  return (
    <CodePre>
      <div className={cn(s['code-wrapper'])}>
        <LineNumbers lineCount={lineCount} />
        <LinesWrapper dataTest="code-wrapper-log-text">
          <div className={s.fallbackPre}>{text}</div>
        </LinesWrapper>
      </div>
    </CodePre>
  );
};

export type CodeHighlighterProps = {
  code: string;
  language: string;
  notCopy?: boolean;
  isSecret?: boolean;
  className?: string;
  CodeTagComponent?: React.ComponentType<DefaultCodeTagProps>;
  dataTest?: string;
};

const CodeHighlighter = ({
  code,
  language,
  isSecret,
  notCopy = false,
  className,
  CodeTagComponent = DefaultCodeTag,
}: CodeHighlighterProps) => {
  const [isSecretVisible, setIsSecretVisible] = useState(!isSecret);
  const text = useMemo(() => (isSecretVisible ? code : code.replace(/./g, '*')), [code, isSecretVisible]);

  const toggleShowSecret = () => {
    setIsSecretVisible((prevValue) => !prevValue);
  };

  return (
    <div className={cn(s.copyCodeWrapper, className)}>
      {!notCopy && <CopyButton code={code} className={s.codeHighlighter__copyBtn} />}
      {isSecret && (
        <IconButton
          className={s.codeHighlighter__showSecretBtn}
          type="button"
          icon={isSecretVisible ? 'eye' : 'eye-crossed'}
          size={20}
          onClick={toggleShowSecret}
        />
      )}
      {language === 'txt' ? (
        <SyntaxFallback text={text} />
      ) : (
        <SyntaxHighlighter
          language={language}
          showLineNumbers={false}
          CodeTag={CodeTagComponent}
          PreTag={CodePre}
          wrapLines={true}
          style={customTheme}
          useInlineStyles={false}
        >
          {text}
        </SyntaxHighlighter>
      )}
    </div>
  );
};

export default CodeHighlighter;
