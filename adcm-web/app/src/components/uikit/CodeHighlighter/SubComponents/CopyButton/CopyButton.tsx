import type React from 'react';
import cn from 'classnames';
import s from './CopyButton.module.scss';
import { useClipboardCopy } from '@hooks';

const TIMEOUT_TO_HIDE_COPIED = 2000;

interface CopyButtonProps {
  code: string;
  className?: string;
}

const CopyButton: React.FC<CopyButtonProps> = ({ code, className }) => {
  const [isCopied, copyToClipboard] = useClipboardCopy(TIMEOUT_TO_HIDE_COPIED);

  const copyButtonStyles = cn(s.copyButton, { isCopied }, className);

  const handleCopy = () => copyToClipboard(code);

  return (
    <button className={copyButtonStyles} onClick={handleCopy}>
      {isCopied ? 'Copied' : 'Copy'}
    </button>
  );
};

export default CopyButton;
