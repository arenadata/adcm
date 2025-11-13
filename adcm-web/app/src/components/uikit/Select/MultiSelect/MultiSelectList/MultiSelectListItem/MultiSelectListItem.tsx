import type React from 'react';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import type { DefaultSelectListItemProps } from '@uikit/Select/Select.types';
import Tooltip from '@uikit/Tooltip/Tooltip';
import s from './MultiSelectListItem.module.scss';
import cn from 'classnames';

export interface MultiSelectListItemProps<T> extends DefaultSelectListItemProps<T>, React.PropsWithChildren {}

const MultiSelectListItem = <T,>({ option, children, className }: MultiSelectListItemProps<T>) => {
  const { title } = option;

  return (
    <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} placement="bottom-start">
      <li className={cn(s.multiSelectListItem, className)}>{children}</li>
    </ConditionalWrapper>
  );
};

export default MultiSelectListItem;
