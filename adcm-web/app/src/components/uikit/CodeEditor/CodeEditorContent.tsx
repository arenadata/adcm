import highlighterStyles from '../CodeHighlighter/CodeHighlighter.module.scss';
import { LineNumbers, LinesWrapper } from '../CodeHighlighter/CodeHighlighter';
import CodeEditorTextArea from './CodeEditorTextArea';
import { HighlighterChildType } from './CodeEditor.types';

export interface CodeEditorContentProps {
  code: string;
  children: HighlighterChildType;
  isReadonly?: boolean;
  onChange: (code: string) => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

const CodeEditorContent = ({ code, children, isReadonly, onChange, onKeyDown }: CodeEditorContentProps) => {
  const [, childArray] = children;
  const rowCount = childArray.length || 1;

  return (
    <div className={highlighterStyles['code-wrapper']}>
      <LineNumbers lineCount={rowCount} />
      <LinesWrapper
        children={childArray}
        subComponent={
          <CodeEditorTextArea
            code={code}
            isReadonly={isReadonly}
            rowCount={rowCount}
            onChange={onChange}
            onKeyDown={onKeyDown}
          />
        }
      />
    </div>
  );
};

export default CodeEditorContent;
