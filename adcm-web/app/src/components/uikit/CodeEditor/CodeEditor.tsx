import { createContext, useContext } from 'react';
import CodeHighlighter from '../CodeHighlighter/CodeHighlighter';
import CodeEditorContent from './CodeEditorContent';
import { HighlighterChildType } from './CodeEditor.types';
import s from './CodeEditor.module.scss';
import cn from 'classnames';

export interface CodeEditorProps {
  code: string;
  language: string;
  className?: string;
  setCode: (code: string) => void;
}

interface CodeProviderInterface extends CodeEditorProps {
  children: React.ReactNode;
}

const CodeCtx = createContext({} as CodeEditorProps);

const CodeProvider = ({ children, code, language, setCode }: CodeProviderInterface) => {
  const codeData = { code, language, setCode };
  return <CodeCtx.Provider value={codeData}>{children}</CodeCtx.Provider>;
};

const TagWithContext: React.FC<{ children: HighlighterChildType }> = ({ children }) => {
  const { code, setCode } = useContext(CodeCtx);

  return <CodeEditorContent children={children} code={code} setCode={setCode} />;
};

const CodeEditor = ({ code, language, className, setCode }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} setCode={setCode} language={language}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} language={language} CodeTagComponent={TagWithContext} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditor;
