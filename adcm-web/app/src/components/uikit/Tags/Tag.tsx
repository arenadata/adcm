import React, { HTMLAttributes } from 'react';
import s from './Tags.module.scss';
import cn from 'classnames';
import { TagOptions } from '@uikit/Tags/Tag.types';

type TagProps = TagOptions & HTMLAttributes<HTMLDivElement>;

const Tag: React.FC<TagProps> = ({ className, isDisabled, children, startAdornment, endAdornment, ...props }) => {
  const classes = cn(className, s.tag, { [s.tag_disabled]: isDisabled });
  return (
    <div className={classes} {...props}>
      {startAdornment}
      {children}
      {endAdornment}
    </div>
  );
};

export default Tag;
