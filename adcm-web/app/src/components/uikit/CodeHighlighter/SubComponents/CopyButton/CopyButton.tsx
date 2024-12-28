import type React from 'react';
import { useEffect, useRef, useState } from 'react';
import cn from 'classnames';
import s from './CopyButton.module.scss';
import { CopyToClipboard } from 'react-copy-to-clipboard';

type CopyButtonProps = {
  code: string;
  className?: string;
};

const CopyButton: React.FC<CopyButtonProps> = ({ code, className }) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const onCopyText = () => {
    setIsCopied(true);

    timerRef.current = setTimeout(() => {
      setIsCopied(false);
    }, 2000);
  };

  useEffect(
    () => () => {
      timerRef.current && clearTimeout(timerRef.current);
    },
    [],
  );

  const copyButtonStyles = cn(s.copyButton, { isCopied: isCopied }, className);

  return (
    <CopyToClipboard text={code} onCopy={onCopyText}>
      <button className={copyButtonStyles}>{isCopied ? 'Copied' : 'Copy'}</button>
    </CopyToClipboard>
  );
};

export default CopyButton;
