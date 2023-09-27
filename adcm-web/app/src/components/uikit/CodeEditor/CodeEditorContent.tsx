import highlighterStyles from '../CodeHighlighter/CodeHighlighter.module.scss';
import { LineNumbers, LinesWrapper } from '../CodeHighlighter/CodeHighlighter';
import CodeEditorTextArea from './CodeEditorTextArea';
import { HighlighterChildType } from './CodeEditor.types';

export interface CodeEditorContentProps {
  code: string;
  children: HighlighterChildType;
  onChange: (code: string) => void;
}

const CodeEditorContent = ({ code, children, onChange }: CodeEditorContentProps) => {
  const [, childArray] = children;
  const rowCount = childArray.length || 1;

  return (
    <div className={highlighterStyles['code-wrapper']}>
      <LineNumbers lineCount={rowCount} />
      <LinesWrapper
        children={childArray}
        subComponent={<CodeEditorTextArea code={code} onChange={onChange} rowCount={rowCount} />}
      />
    </div>
  );
};

export default CodeEditorContent;
