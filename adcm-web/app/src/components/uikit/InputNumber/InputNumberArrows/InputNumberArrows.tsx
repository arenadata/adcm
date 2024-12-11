import type React from 'react';
import IconButton from '@uikit/IconButton/IconButton';

import s from './InputNumberArrows.module.scss';

interface InputNumberArrowsProps {
  disabled?: boolean;
  onStepUp: () => void;
  onStepDown: () => void;
}
const InputNumberArrows: React.FC<InputNumberArrowsProps> = ({ disabled, onStepUp, onStepDown }) => {
  return (
    <div className={s.inputNumberArrows}>
      <IconButton
        icon="chevron"
        size={10}
        onClick={onStepUp}
        tabIndex={-1}
        disabled={disabled}
        className={s.inputNumberArrows__arrowUp}
      />
      <IconButton
        //
        icon="chevron"
        size={10}
        onClick={onStepDown}
        tabIndex={-1}
        disabled={disabled}
      />
    </div>
  );
};
export default InputNumberArrows;
