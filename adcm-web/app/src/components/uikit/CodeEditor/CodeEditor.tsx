import { createContext, useContext } from 'react';
import CodeHighlighter from '../CodeHighlighter/CodeHighlighter';
import CodeEditorTextArea from './CodeEditorTextArea';
import { getLines } from '@uikit/CodeHighlighter/CodeHighlighterHelper';
import s from './CodeEditor.module.scss';
import cn from 'classnames';

export interface CodeEditorProps {
  code: string;
  language: string;
  isSecret?: boolean;
  className?: string;
  isReadonly?: boolean;
  onChange: (code: string) => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

interface CodeProviderInterface extends CodeEditorProps {
  children: React.ReactNode;
}

const CodeCtx = createContext({} as CodeEditorProps);

const CodeProvider = ({ children, code, language, isReadonly, onChange, onKeyDown }: CodeProviderInterface) => {
  const codeData = { code, language, isReadonly, onChange, onKeyDown };
  return <CodeCtx.Provider value={codeData}>{children}</CodeCtx.Provider>;
};

const TagWithContext = () => {
  const { code, isReadonly, onChange, onKeyDown } = useContext(CodeCtx);
  const rowCount = getLines(code).length;

  return (
    <CodeEditorTextArea
      code={code}
      isReadonly={isReadonly}
      rowCount={rowCount}
      onChange={onChange}
      onKeyDown={onKeyDown}
    />
  );
};

const CodeEditor = ({ code, language, isSecret, className, isReadonly, onChange, onKeyDown }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} onChange={onChange} onKeyDown={onKeyDown} language={language} isReadonly={isReadonly}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} language={language} isSecret={isSecret} codeOverlay={<TagWithContext />} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditor;
