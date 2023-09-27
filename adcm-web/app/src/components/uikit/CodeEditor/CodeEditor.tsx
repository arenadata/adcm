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
  onChange: (code: string) => void;
}

interface CodeProviderInterface extends CodeEditorProps {
  children: React.ReactNode;
}

const CodeCtx = createContext({} as CodeEditorProps);

const CodeProvider = ({ children, code, language, onChange }: CodeProviderInterface) => {
  const codeData = { code, language, onChange };
  return <CodeCtx.Provider value={codeData}>{children}</CodeCtx.Provider>;
};

const TagWithContext: React.FC<{ children: HighlighterChildType }> = ({ children }) => {
  const { code, onChange } = useContext(CodeCtx);

  return <CodeEditorContent children={children} code={code} onChange={onChange} />;
};

const CodeEditor = ({ code, language, isSecret, className, onChange }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} onChange={onChange} language={language}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} language={language} isSecret={isSecret} CodeTagComponent={TagWithContext} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditor;
