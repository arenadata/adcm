import { createContext, useContext } from 'react';
import CodeHighlighter from '../CodeHighlighterV2/CodeHighlighterV2';
import s from './CodeEditorV2.module.scss';
import cn from 'classnames';
import CodeEditorTextAreaV2 from '@uikit/CodeEditorV2/CodeEditorTextAreaV2';
import { getLines } from '@uikit/CodeHighlighterV2/CodeHighlighterHelperV2';

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

const TagWithContext = () => {
  const { code, isReadonly, onChange } = useContext(CodeCtx);
  const rowCount = getLines(code).length;

  return <CodeEditorTextAreaV2 code={code} onChange={onChange} isReadonly={isReadonly} rowCount={rowCount} />;
};

const CodeEditorV2 = ({ code, language, isSecret, className, isReadonly, onChange }: CodeEditorProps) => {
  return (
    <CodeProvider code={code} onChange={onChange} language={language} isReadonly={isReadonly}>
      <div className={cn(s.codeEditor, className)}>
        <CodeHighlighter code={code} lang={language} isSecret={isSecret} codeOverlay={<TagWithContext />} />
      </div>
    </CodeProvider>
  );
};

export default CodeEditorV2;
