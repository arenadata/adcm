import React from 'react';
import cn from 'classnames';
import { allowIconsNames, IconsNames } from './sprite';
import { Sizes } from '../utils/types';

allowIconsNames.forEach(async (name) => {
  await import(`./icons/${name}.svg`);
});

const iconSizesConfig: { [key in Sizes]: number } = {
  small: 12,
  medium: 20,
  large: 24,
};
export interface IconProps extends React.SVGAttributes<SVGSVGElement> {
  size?: Sizes | number;
  name: IconsNames;
}

const Icon = React.forwardRef<SVGSVGElement, IconProps>(({ name, size = 'medium', className, ...props }, ref) => {
  const classString = cn('icon', className);

  const sizeVal = iconSizesConfig[size as Sizes] ?? size;

  return (
    <svg className={classString} width={sizeVal} height={sizeVal} {...props} ref={ref}>
      <use href={`#icon-${name}`} />
    </svg>
  );
});

Icon.displayName = 'Icon';

export default Icon;
