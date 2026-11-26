import { useMemo } from 'react';
import type { HTMLReactParserOptions } from 'html-react-parser';
import parse, { Element } from 'html-react-parser';
import cn from 'classnames';
import s from './MainInfoPanel.module.scss';
import { sanitizeAllowedHtml } from '@utils/sanitizeUtils';

interface MainInfoPanelProps {
  className?: string;
  mainInfo?: string;
}

const parseOptions: HTMLReactParserOptions = {
  replace: (domNode) => {
    if (domNode instanceof Element && domNode.attribs) {
      if (domNode.name === 'a') {
        const existingClass = domNode.attribs.class ?? '';
        domNode.attribs.class = [existingClass, 'text-link'].filter(Boolean).join(' ');
      }

      if (domNode.name === 'ul') {
        const existingClass = domNode.attribs.class ?? '';
        domNode.attribs.class = [existingClass, 'marked-list'].filter(Boolean).join(' ');
      }
    }

    return domNode;
  },
};

const MainInfoPanel = ({ mainInfo, className }: MainInfoPanelProps) => {
  const parsedMainInfo = useMemo(() => {
    if (!mainInfo) return null;

    const sanitizedMainInfo = sanitizeAllowedHtml(mainInfo);

    return parse(sanitizedMainInfo, parseOptions);
  }, [mainInfo]);

  return <div className={cn(className, s.mainInfoPanel)}>{parsedMainInfo}</div>;
};

export default MainInfoPanel;
