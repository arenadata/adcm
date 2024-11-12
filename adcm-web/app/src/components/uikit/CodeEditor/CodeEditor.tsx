import { createContext, useContext } from 'react';
import CodeHighlighter from '../CodeHighlighter/CodeHighlighter';
import CodeEditorContent from './CodeEditorContent';
import type { HighlighterChildType } from './CodeEditor.types';
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

const TagWithContext: React.FC<{ children: HighlighterChildType }> = ({ children }) => {
  const { code, isReadonly, onChange, onKeyDown } = useContext(CodeCtx);

  return (
    <CodeEditorContent
      children={children}
      code={code}
      isReadonly={isReadonly}
      onChange={onChange}
      onKeyDown={onKeyDown}
    />
  );
};

const CodeEditor = ({ code, language, isSecret, className, isReadonly, onChange, onKeyDown }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} onChange={onChange} onKeyDown={onKeyDown} language={language} isReadonly={isReadonly}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} language={language} isSecret={isSecret} CodeTagComponent={TagWithContext} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditor;
