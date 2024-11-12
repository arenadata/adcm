import type { ChangeEventHandler, RefObject } from 'react';
import React, { useRef } from 'react';
import cn from 'classnames';
import type { InputProps } from '@uikit/Input/Input';
import Input from '@uikit/Input/Input';
import { useForwardRef } from '@hooks';
import InputNumberArrows from '@uikit/InputNumber/InputNumberArrows/InputNumberArrows';
import { createChangeEvent } from '@utils/handlerUtils';

import s from './InputNumber.module.scss';

type InputNumberV2Props = Omit<InputProps, 'type' | 'endAdornment' | 'startAdornment'>;

const InputNumber = React.forwardRef<HTMLInputElement, InputNumberV2Props>(
  ({ className, onChange, disabled, readOnly, ...props }, ref) => {
    const localRef = useRef<HTMLInputElement>(null);
    const reference = useForwardRef(ref, localRef);

    const handleStepUp = () =>
      handleStep({
        direction: 'up',
        ref: localRef,
        onChange,
      });
    const handleStepDown = () =>
      handleStep({
        direction: 'down',
        ref: localRef,
        onChange,
      });

    return (
      <Input
        className={cn(className, s.inputNumber)}
        type="number"
        ref={reference}
        onChange={onChange}
        disabled={disabled}
        readOnly={readOnly}
        endAdornment={
          <InputNumberArrows onStepUp={handleStepUp} onStepDown={handleStepDown} disabled={disabled || readOnly} />
        }
        {...props}
      />
    );
  },
);

InputNumber.displayName = 'InputNumber';
export default InputNumber;

interface HandleStepParams {
  direction: 'up' | 'down';
  ref: RefObject<HTMLInputElement> | null;
  onChange?: ChangeEventHandler;
  successCallback?: (val: string) => void;
}
const handleStep = ({ direction, ref, onChange, successCallback }: HandleStepParams) => {
  if (!ref?.current) return;

  const target = ref.current;
  const prevValue = target.value;

  // safari crashes when call stepUp/stepDown with unset value
  if (prevValue === '') {
    target.value = '0';
  }

  if (direction === 'up') {
    target.stepUp();
  } else {
    target.stepDown();
  }
  const result = target.value;

  successCallback && successCallback(result);

  if (result === prevValue || !onChange) return;

  const changeEvent = createChangeEvent(target);
  changeEvent.target.value = result;

  onChange(changeEvent);
};
