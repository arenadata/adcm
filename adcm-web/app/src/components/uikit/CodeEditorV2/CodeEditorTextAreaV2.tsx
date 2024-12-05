import shortcuts from './shortcuts';
import highlighterStyles from '../CodeHighlighterV2/CodeHighlighterV2.module.scss';
import s from './CodeEditorV2.module.scss';
import cn from 'classnames';

interface CodeEditorTextAreaProps {
  code: string;
  rowCount: number;
  isReadonly?: boolean;
  onChange: (code: string) => void;
}

const CodeEditorTextAreaV2 = ({ code, rowCount, isReadonly, onChange }: CodeEditorTextAreaProps) => {
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
      }}
      rows={rowCount}
      cols={longestRow}
      onChange={(event) => {
        onChange(event.target.value);
      }}
      className={cn(s.codeEditor__textArea, highlighterStyles.codeHighlighterFontParams)}
      readOnly={isReadonly}
      value={code}
    />
  );
};

export default CodeEditorTextAreaV2;
