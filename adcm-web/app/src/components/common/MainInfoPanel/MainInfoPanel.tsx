import React, { useMemo } from 'react';
import parse, { HTMLReactParserOptions, Element } from 'html-react-parser';
import cn from 'classnames';
import s from './MainInfoPanel.module.scss';

interface MainInfoPanelProps {
  className?: string;
  mainInfo?: string;
}

const MainInfoPanel = ({ mainInfo, className }: MainInfoPanelProps) => {
  const parsedMainInfo = useMemo(() => {
    if (!mainInfo) return null;

    const parseOptions: HTMLReactParserOptions = {
      replace: (domNode) => {
        if (domNode instanceof Element && domNode.attribs && domNode.name === 'a') {
          domNode.attribs.class = [domNode.attribs.class, 'text-link'].join(' ');
        }
        return domNode;
      },
    };

    return parse(mainInfo, parseOptions);
  }, [mainInfo]);

  return <div className={cn(className, s.mainInfoPanel)}>{parsedMainInfo}</div>;
};

export default MainInfoPanel;
