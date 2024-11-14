import type { HTMLAttributes } from 'react';
import React from 'react';
import s from './Tags.module.scss';
import cn from 'classnames';
import type { TagOptions } from '@uikit/Tags/Tag.types';

type TagProps = TagOptions & HTMLAttributes<HTMLDivElement>;

const Tag: React.FC<TagProps> = ({
  className,
  isDisabled,
  children,
  startAdornment,
  endAdornment,
  variant = 'primary',
  ...props
}) => {
  const classes = cn(className, s.tag, { [s.tag_disabled]: isDisabled }, s[`tag__${variant}`]);
  return (
    <div className={classes} {...props}>
      {startAdornment}
      {children}
      {endAdornment}
    </div>
  );
};

export default Tag;
