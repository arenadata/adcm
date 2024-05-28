import React from 'react';
import cn from 'classnames';
import type { IconsNames } from './sprite';
import type { Size } from '@uikit/types/size.types';

const iconSizesConfig: { [key in Size]: number } = {
  small: 12,
  medium: 20,
  large: 24,
};
export interface IconProps extends React.SVGAttributes<SVGSVGElement> {
  size?: Size | number;
  name: IconsNames;
}

const Icon = React.forwardRef<SVGSVGElement, IconProps>(({ name, size = 'medium', className, ...props }, ref) => {
  const classString = cn('icon', className);

  const sizeVal = iconSizesConfig[size as Size] ?? size;

  return (
    <svg className={classString} width={sizeVal} height={sizeVal} {...props} ref={ref}>
      <use xlinkHref={`#${name}`} />
    </svg>
  );
});

Icon.displayName = 'Icon';

export default Icon;
