import type React from 'react';
import { useState } from 'react';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import Text from '@uikit/Text/Text';
import Collapse from '@uikit/Collapse/Collapse';
import type { BaseComponentProps } from '@utils/types';
import s from './PageSection.module.scss';
import cn from 'classnames';
import Icon from '@uikit/Icon/Icon';
import { textToDataTestValue } from '@utils/dataTestUtils';

interface PageSectionProps extends BaseComponentProps {
  title: React.ReactNode;
  isExpandDefault?: boolean;
  hasError?: boolean;
  dataTest?: string;
  headerActions?: React.ReactNode;
}

const PageSection: React.FC<PageSectionProps> = ({
  title,
  className,
  children,
  isExpandDefault = true,
  hasError = false,
  dataTest,
  headerActions,
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
      <FlexGroup className={s.pageSection__header} gap="var(--space-400)" justifyContent="space-between">
        <Text variant="h2" data-test="page-section-title">
          <button
            type="button"
            className={cn(s.pageSection__title, 'green-text')}
            aria-expanded={isExpand}
            onClick={toggle}
            data-test="page-section-toggle"
          >
            {title}
            <Icon name="chevron" size={12} className={s.pageSection__arrow} />
          </button>
        </Text>
        {headerActions}
      </FlexGroup>
      <Collapse isExpanded={isExpand} data-test="page-section-content">
        <div className={s.pageSection__collapseBody}>{children}</div>
      </Collapse>
    </section>
  );
};

export default PageSection;
