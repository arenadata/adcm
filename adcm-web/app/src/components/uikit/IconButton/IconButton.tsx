import React from 'react';
import cn from 'classnames';
import s from './IconButton.module.scss';
import ConditionalWrapper from '@uikit/ConditionalWrapper/ConditionalWrapper';
import { textToDataTestValue } from '@utils/dataTestUtils';
import { IconsNames } from '@uikit/Icon/sprite';
import Icon, { IconProps } from '@uikit/Icon/Icon';
import Tooltip, { TooltipProps } from '@uikit/Tooltip/Tooltip';

type IconButtonVariant = 'primary' | 'secondary';
export interface IconButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'children' | 'title'> {
  icon: IconsNames;
  size?: IconProps['size'];
  variant?: IconButtonVariant;
  title?: TooltipProps['label'];
  tooltipProps?: Omit<TooltipProps, 'label' | 'children'>;
  dataTest?: string;
}

const IconButton = React.forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    { icon, size = 32, variant = 'primary', className: outerClassName, title, tooltipProps, dataTest, ...props },
    ref,
  ) => {
    const className = cn(outerClassName, s.iconButton, s[`iconButton_${variant}`]);
    const dataTestValue = dataTest ? dataTest : (typeof title === 'string' && textToDataTestValue(title)) || undefined;
    const otherProps = { ['data-test']: dataTestValue, ...props };

    return (
      <ConditionalWrapper Component={Tooltip} isWrap={!!title} label={title} {...tooltipProps}>
        <button className={className} {...otherProps} ref={ref}>
          <Icon name={icon} size={size} />
        </button>
      </ConditionalWrapper>
    );
  },
);

IconButton.displayName = 'IconButton';

export default IconButton;
