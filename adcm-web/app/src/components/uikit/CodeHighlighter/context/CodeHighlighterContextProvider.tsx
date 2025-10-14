import type React from 'react';
import { useState } from 'react';
import { CodeHighlighterContext } from './CodeHighlighter.context';

interface CodeHighlighterContextProvider {
  children: React.ReactNode;
}

export const CodeHighlighterContextProvider: React.FC<CodeHighlighterContextProvider> = ({ children }) => {
  const [isFullScreen, setIsFullScreen] = useState(false);

  return (
    <CodeHighlighterContext.Provider value={{ isFullScreen, setIsFullScreen }}>
      {children}
    </CodeHighlighterContext.Provider>
  );
};
