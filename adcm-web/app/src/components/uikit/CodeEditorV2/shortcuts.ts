/* eslint-disable spellcheck/spell-checker */
import React from 'react';
import { SelectionText } from './CodeEditorV2.types.ts';

function stopPropagation(e: React.KeyboardEvent<HTMLTextAreaElement>) {
  e.stopPropagation();
  e.preventDefault();
}

export default function shortcuts(e: React.KeyboardEvent<HTMLTextAreaElement>) {
  const api = new SelectionText(e.target as HTMLTextAreaElement);
  /**
   * Support of shortcuts for React v16
   * https://github.com/uiwjs/react-textarea-code-editor/issues/128
   * https://blog.saeloun.com/2021/04/23/react-keyboard-event-code.html
   */
  const code = (e.code || e.nativeEvent.code).toLocaleLowerCase();
  if (code === 'tab') {
    stopPropagation(e);
    if (api.start === api.end) {
      api.insertText('  ').position(api.start + 2, api.end + 2);
    } else if (api.getSelectedValue().indexOf('\n') > -1 && e.shiftKey) {
      api.lineStarRemove('  ');
    } else if (api.getSelectedValue().indexOf('\n') > -1) {
      api.lineStarInsert('  ');
    } else {
      api.insertText('  ').position(api.start + 2, api.end);
    }
    api.notifyChange();
  } else if (code === 'enter') {
    stopPropagation(e);
    const indent = `\n${api.getIndentText()}`;
    api.insertText(indent).position(api.start + indent.length, api.start + indent.length);
    api.notifyChange();
  } else if (code && /^(quote|backquote|bracketleft|digit9|comma)$/.test(code) && api.getSelectedValue()) {
    stopPropagation(e);
    const val = api.getSelectedValue();
    let text = '';
    switch (code) {
      case 'quote':
        text = `'${val}'`;
        if (e.shiftKey) {
          text = `"${val}"`;
        }
        break;
      case 'backquote':
        text = `\`${val}\``;
        break;
      case 'bracketleft':
        text = `[${val}]`;
        if (e.shiftKey) {
          text = `{${val}}`;
        }
        break;
      case 'digit9':
        text = `(${val})`;
        break;
      case 'comma':
        text = `<${val}>`;
        break;
    }
    api.insertText(text);
    api.notifyChange();
  }
}
