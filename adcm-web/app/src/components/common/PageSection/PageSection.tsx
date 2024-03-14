import React, { useState } from 'react';
import Text from '@uikit/Text/Text';
import Collapse from '@uikit/Collapse/Collapse';
import { BaseComponentProps } from '@utils/types';
import s from './PageSection.module.scss';
import cn from 'classnames';
import Icon from '@uikit/Icon/Icon';
import { textToDataTestValue } from '@utils/dataTestUtils';

interface PageSectionProps extends BaseComponentProps {
  title: React.ReactNode;
  isExpandDefault?: boolean;
  hasError?: boolean;
  dataTest?: string;
}

const PageSection: React.FC<PageSectionProps> = ({
  title,
  className,
  children,
  isExpandDefault = true,
  hasError = false,
  dataTest,
}) => {
  const [isExpand, setIsExpand] = useState<boolean>(isExpandDefault);
  const dataTestValue = dataTest
    ? dataTest
    : (typeof title === 'string' && textToDataTestValue(title)) || 'page-section';
  const toggle = () => {
    setIsExpand((prev) => !prev);
  };
  const sectionClassName = cn(s.pageSection, className, {
    [s.pageSection_isOpen]: isExpand,
    [s.pageSection_hasErrors]: hasError,
  });
  return (
    <section className={sectionClassName} data-test={dataTestValue}>
      <Text variant="h2" data-test="page-section-title">
        <div onClick={toggle} className={s.pageSection__title}>
          {title} <Icon name="chevron" size={12} className={s.pageSection__arrow} />
        </div>
      </Text>
      <Collapse isExpanded={isExpand} data-test="page-section-content">
        <div className={s.pageSection__collapseBody}>{children}</div>
      </Collapse>
    </section>
  );
};

export default PageSection;
