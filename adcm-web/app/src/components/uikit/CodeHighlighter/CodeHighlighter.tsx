import React from 'react';
import cn from 'classnames';
import s from './CodeHighlighter.module.scss';
import './Themes/CodeHighlighter.module.themes.scss';
import SyntaxHighlighter from 'react-syntax-highlighter';
import customTheme from './Themes/customTheme';
import CopyButton from './CopyButton/CopyButton';

type LinesWrapperProps = {
  children: React.ReactNode;
  subComponent?: React.ReactElement;
};

interface DefaultCodeTagProps extends React.PropsWithChildren {
  children: [boolean, React.ReactNode[]];
  linesWrapper?: React.ReactElement;
}

type LineNumbersProps = {
  lineCount: number;
};

export const LinesWrapper = ({ children }: LinesWrapperProps) => {
  return <div className={cn(s['code-wrapper__code-lines'])}>{children}</div>;
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
      <LinesWrapper>{childArray}</LinesWrapper>
    </div>
  );
};

const CodePre = ({ children }: React.PropsWithChildren) => (
  <div className={cn(s['code-pre'], s['highlighter_font-params'])}>{children}</div>
);

export type CodeHighlighterProps = {
  code: string;
  language: string;
  notCopy?: boolean;
  CodeTagComponent?: React.ComponentType<DefaultCodeTagProps>;
};

const CodeHighlighter = ({
  code,
  language,
  notCopy = false,
  CodeTagComponent = DefaultCodeTag,
}: CodeHighlighterProps) => {
  return (
    <div className={s.copyCodeWrapper}>
      {!notCopy && <CopyButton code={code} className={s.codeHighlighter__copyBtn} />}
      <SyntaxHighlighter
        language={language}
        showLineNumbers={false}
        CodeTag={CodeTagComponent}
        PreTag={CodePre}
        wrapLines={true}
        style={customTheme}
        useInlineStyles={false}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeHighlighter;
