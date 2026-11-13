import type React from 'react';
import cn from 'classnames';
import { Icon, Tooltip } from '@uikit';
import type { IconsNames } from '@uikit';
import s from './JobActionIconButton.module.scss';

const ICON_SIZE = 16;

export type JobActionIconButtonProps = {
  icon: IconsNames;
  label: string;
  disabled?: boolean;
  className?: string;
  'data-test'?: string;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
};

export const JobActionIconButton = ({
  icon,
  label,
  disabled,
  className,
  onClick,
  'data-test': dataTest,
}: JobActionIconButtonProps) => {
  return (
    <Tooltip label={label} placement="top">
      <button
        type="button"
        className={cn(s.button, className)}
        disabled={disabled}
        onClick={onClick}
        data-test={dataTest}
      >
        <Icon name={icon} size={ICON_SIZE} />
      </button>
    </Tooltip>
  );
};
