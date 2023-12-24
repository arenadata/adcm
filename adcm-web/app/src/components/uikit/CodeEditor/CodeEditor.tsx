import { createContext, useContext } from 'react';
import CodeHighlighter from '../CodeHighlighter/CodeHighlighter';
import CodeEditorContent from './CodeEditorContent';
import { HighlighterChildType } from './CodeEditor.types';
import s from './CodeEditor.module.scss';
import cn from 'classnames';

export interface CodeEditorProps {
  code: string;
  language: string;
  isSecret?: boolean;
  className?: string;
  isReadonly?: boolean;
  onChange: (code: string) => void;
}

interface CodeProviderInterface extends CodeEditorProps {
  children: React.ReactNode;
}

const CodeCtx = createContext({} as CodeEditorProps);

const CodeProvider = ({ children, code, language, isReadonly, onChange }: CodeProviderInterface) => {
  const codeData = { code, language, isReadonly, onChange };
  return <CodeCtx.Provider value={codeData}>{children}</CodeCtx.Provider>;
};

const TagWithContext: React.FC<{ children: HighlighterChildType }> = ({ children }) => {
  const { code, isReadonly, onChange } = useContext(CodeCtx);

  return <CodeEditorContent children={children} code={code} isReadonly={isReadonly} onChange={onChange} />;
};

const CodeEditor = ({ code, language, isSecret, className, isReadonly, onChange }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} onChange={onChange} language={language} isReadonly={isReadonly}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} language={language} isSecret={isSecret} CodeTagComponent={TagWithContext} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditor;
