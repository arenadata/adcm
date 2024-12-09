import shortcuts from './shortcuts';
import highlighterStyles from '../CodeHighlighter/CodeHighlighter.module.scss';
import s from './CodeEditor.module.scss';
import cn from 'classnames';

interface CodeEditorTextAreaProps {
  code: string;
  rowCount: number;
  isReadonly?: boolean;
  onChange: (code: string) => void;
  onKeyDown?: (event: React.KeyboardEvent<HTMLTextAreaElement>) => void;
}

const CodeEditorTextArea = ({ code, rowCount, isReadonly, onChange, onKeyDown }: CodeEditorTextAreaProps) => {
  const longestRow = code.split('\n').reduce((longest, row) => {
    return longest < row.length ? row.length : longest;
  }, 0);

  return (
    <textarea
      autoComplete="off"
      autoCorrect="off"
      spellCheck="false"
      autoCapitalize="off"
      onKeyDown={(event) => {
        shortcuts(event);
        onKeyDown?.(event);
      }}
      rows={rowCount}
      cols={longestRow}
      onChange={(event) => {
        onChange(event.target.value);
      }}
      className={cn(s.codeEditor__textArea, highlighterStyles['highlighter_font-params'])}
      readOnly={isReadonly}
      value={code}
    />
  );
};

export default CodeEditorTextArea;
