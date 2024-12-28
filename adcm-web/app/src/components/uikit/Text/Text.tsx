import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';
import s from './Text.module.scss';

type TagType = keyof Pick<React.ReactHTML, 'h1' | 'h2' | 'h3' | 'h4'>;

export interface TextProps extends HTMLAttributes<HTMLElement> {
  variant: TagType;
  component?: TagType | null;
}

const Text = ({ variant, component = null, className, children, ...props }: TextProps) => {
  const textClasses = cn(s.text, className, s[`text_${variant}`]);
  const Tag = component ?? variant;

  return (
    <Tag className={textClasses} {...props}>
      {children}
    </Tag>
  );
};

export default Text;
