import type { RefObject } from 'react';
import type React from 'react';
import { useEffect, useRef } from 'react';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import type { AdcmSubJobLogItemCustom, AdcmSubJobLogItemStd } from '@models/adcm';
import s from './SubJobLogText.module.scss';

interface SubJobLogTextProps {
  log: AdcmSubJobLogItemStd | AdcmSubJobLogItemCustom;
  isAutoScroll: boolean;
  setIsAutoScroll?: (isAutoScroll: boolean) => void;
}

const SubJobLogText: React.FC<SubJobLogTextProps> = ({ log, isAutoScroll, setIsAutoScroll }) => {
  const content = log.content?.trim() || '';
  const language = log.format === 'json' ? 'json' : 'bash';
  const highlighterRef: RefObject<HTMLDivElement> = useRef(null);
  const isUserScrollRef = useRef(true);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!highlighterRef?.current || !isAutoScroll) return;

    timer.current = window.setTimeout(() => {
      if (!isAutoScroll) return;
      requestAnimationFrame(() => {
        isUserScrollRef.current = false;
        highlighterRef?.current?.scrollTo({ left: 0, top: highlighterRef?.current.scrollHeight, behavior: 'smooth' });
      });
    }, 260);

    return () => {
      if (!timer.current) return;
      window.clearTimeout(timer.current);
    };
  }, [highlighterRef, isAutoScroll, log]);

  useEffect(() => {
    if (!setIsAutoScroll || !highlighterRef.current) return;
    const onUserScrollHandler = () => {
      if (isUserScrollRef.current) {
        setIsAutoScroll(false);
      }
    };

    const onEndHandler = () => {
      isUserScrollRef.current = true;
    };

    const current = highlighterRef.current;

    if (isAutoScroll) {
      current.addEventListener('scroll', onUserScrollHandler);
      current.addEventListener('scrollend', onEndHandler);
    }

    return () => {
      current?.removeEventListener('scroll', onUserScrollHandler);
      current?.removeEventListener('scrollend', onEndHandler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAutoScroll, highlighterRef]);

  return <CodeHighlighter contentRef={highlighterRef} className={s.subJobLogText} code={content} language={language} />;
};
export default SubJobLogText;
