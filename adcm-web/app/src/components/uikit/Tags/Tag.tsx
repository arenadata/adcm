import React, { HTMLAttributes } from 'react';
import s from './Tags.module.scss';
import cn from 'classnames';
import { TagOptions } from '@uikit/Tags/Tag.types';

type TagProps = TagOptions & HTMLAttributes<HTMLDivElement>;

const Tag: React.FC<TagProps> = ({ className, children, startAdornment, endAdornment, ...props }) => {
  return (
    <div className={cn(className, s.tag)} {...props}>
      {startAdornment}
      {children}
      {endAdornment}
    </div>
  );
};

export default Tag;
