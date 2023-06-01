import React, { useState } from 'react';
import Text from '@uikit/Text/Text';
import Collapse from '@uikit/Collapse/Collapse';
import { BaseComponentProps } from '@utils/types';
import s from './PageSection.module.scss';
import cn from 'classnames';
import Icon from '@uikit/Icon/Icon';

interface PageSectionProps extends BaseComponentProps {
  title: React.ReactNode;
  isExpandDefault?: boolean;
  hasError?: boolean;
}

const PageSection: React.FC<PageSectionProps> = ({
  title,
  className,
  children,
  isExpandDefault = true,
  hasError = false,
}) => {
  const [isExpand, setIsExpand] = useState<boolean>(isExpandDefault);
  const toggle = () => {
    setIsExpand((prev) => !prev);
  };
  const sectionClassName = cn(s.pageSection, className, {
    [s.pageSection_isOpen]: isExpand,
    [s.pageSection_hasErrors]: hasError,
  });
  return (
    <section className={sectionClassName}>
      <Text variant="h2">
        <div onClick={toggle} className={s.pageSection__title}>
          {title} <Icon name="chevron" size={12} className={s.pageSection__arrow} />
        </div>
      </Text>
      <Collapse isExpanded={isExpand}>
        <div className={s.pageSection__collapseBody}>{children}</div>
      </Collapse>
    </section>
  );
};

export default PageSection;
