import React from 'react';
import type { SwitchProps } from './Switch';
import Switch from './Switch';
import s from './ExpandableSwitch.module.scss';

export interface ExpandableSwitchProps extends SwitchProps {
  label: string;
}

const ExpandableSwitch = ({ label, ...rest }: ExpandableSwitchProps) => {
  return (
    <div className={s.expandableSwitch}>
      <div className={s.expandableSwitch__label}>{label}</div>
      <Switch {...rest} />
    </div>
  );
};

export default ExpandableSwitch;
