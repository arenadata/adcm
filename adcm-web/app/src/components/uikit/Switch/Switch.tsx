import React from 'react';
import s from './Switch.module.scss';
import cn from 'classnames';

type SwitchSize = 'medium' | 'small';

export interface SwitchProps {
  isToggled: boolean;
  id?: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  className?: string;
  disabled?: boolean;
  label?: string;
  size?: SwitchSize;
}

const Switch = ({
  isToggled = false,
  disabled = false,
  className,
  id,
  size = 'medium',
  onChange,
  label,
  ...rest
}: SwitchProps) => {
  const switchClassName = cn(className, s.switch, s[`switch_${size}`]);

  return (
    <label className={switchClassName}>
      <input
        id={id}
        checked={isToggled}
        onChange={onChange}
        className={s.switchCheckbox}
        type="checkbox"
        disabled={disabled}
        {...rest}
      />
      <span className={s.switchLabel}></span>
      {label || null}
    </label>
  );
};

export default Switch;
