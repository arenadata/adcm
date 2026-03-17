import type React from 'react';
import CopyButton from '@uikit/CodeHighlighter/SubComponents/CopyButton/CopyButton';
import Button from '@uikit/Button/Button';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import cn from 'classnames';
import s from './MonacoCodeEditorToolbar.module.scss';

export interface MonacoCodeEditorToolbarProps {
  className?: string;
  code: string;
  showCopyButton?: boolean;
  showFullscreenButton?: boolean;
  isFullscreenActive?: boolean;
  onExpandClick?: () => void;
}

const MonacoCodeEditorToolbar: React.FC<MonacoCodeEditorToolbarProps> = ({
  className,
  code,
  showCopyButton = false,
  showFullscreenButton = false,
  isFullscreenActive = false,
  onExpandClick,
}) => {
  if (!showCopyButton && !showFullscreenButton) {
    return null;
  }

  return (
    <div className={cn(s.toolbar, className)}>
      <FlexGroup gap="4px">
        {showFullscreenButton && !isFullscreenActive && (
          <Button
            iconLeft="g2-expand"
            variant="tertiary"
            tooltipProps={{ placement: 'left' }}
            title="Full screen"
            onClick={onExpandClick}
            className={s.toolbar__expandBtn}
          />
        )}
        {showCopyButton && (
          <span data-toolbar-copy>
            <CopyButton code={code} className={s.toolbar__copyBtn} />
          </span>
        )}
      </FlexGroup>
    </div>
  );
};

export default MonacoCodeEditorToolbar;
