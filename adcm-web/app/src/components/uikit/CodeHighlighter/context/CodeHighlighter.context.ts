import type { Context } from 'react';
import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';

interface CodeHighlighterContextOptions {
  isFullScreen: boolean;
  setIsFullScreen: (isFullScreen: boolean) => void;
}

export const CodeHighlighterContext = createContextHelper<CodeHighlighterContextOptions>('CodeHighlighterContext');

export const useCodeHighlighterContext = (): CodeHighlighterContextOptions =>
  useContextHelper<CodeHighlighterContextOptions>(
    CodeHighlighterContext as Context<CodeHighlighterContextOptions | undefined>,
  );
