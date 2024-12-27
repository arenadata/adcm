import { useState, useEffect } from 'react';
import { copy } from './helper';

/**
 * @param successDuration - timeout in milliseconds for switching isCopied back to false
 * */
export function useClipboardCopy(successDuration = 0): [boolean, (text: string) => void] {
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    if (isCopied && successDuration) {
      const id = setTimeout(() => {
        setIsCopied(false);
      }, successDuration);

      return () => clearTimeout(id);
    }
  }, [isCopied, successDuration]);

  const handleCopy = async (text: string) => {
    const didCopy = await copy(text);
    setIsCopied(didCopy);
  };

  return [isCopied, handleCopy];
}
