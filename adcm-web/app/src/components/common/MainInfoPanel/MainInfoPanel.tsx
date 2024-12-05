import { useMemo } from 'react';
import type { HTMLReactParserOptions } from 'html-react-parser';
import parse, { Element } from 'html-react-parser';
import cn from 'classnames';
import s from './MainInfoPanel.module.scss';

interface MainInfoPanelProps {
  className?: string;
  mainInfo?: string;
}

const parseOptions: HTMLReactParserOptions = {
  replace: (domNode) => {
    if (domNode instanceof Element && domNode.attribs) {
      if (domNode.name === 'a') {
        domNode.attribs.class = [domNode.attribs.class, 'text-link'].join(' ');
      }

      if (domNode.name === 'ul') {
        domNode.attribs.class = [domNode.attribs.class, 'marked-list'].join(' ');
      }
    }

    return domNode;
  },
};

const MainInfoPanel = ({ mainInfo, className }: MainInfoPanelProps) => {
  const parsedMainInfo = useMemo(() => {
    if (!mainInfo) return null;

    return parse(mainInfo, parseOptions);
  }, [mainInfo]);

  return <div className={cn(className, s.mainInfoPanel)}>{parsedMainInfo}</div>;
};

export default MainInfoPanel;
