import type React from 'react';
import { useEffect, useState } from 'react';
import { useFieldStyles } from '@uikit/Field/useFieldStyles';
import type { ChangeDateHandler } from '@uikit/DatePicker/DatePicker.types';
import { format, isValid } from '@utils/date';
import s from './InputTime.module.scss';
import cn from 'classnames';

interface InputTimeProps {
  date: Date;
  onChange: ChangeDateHandler;
}

const InputTime = ({ onChange, date }: InputTimeProps) => {
  const [hours, setInnerHours] = useState(format(date, 'HH'));
  const [minutes, setInnerMinutes] = useState(format(date, 'mm'));

  useEffect(() => {
    setInnerHours(format(date, 'HH'));
    setInnerMinutes(format(date, 'mm'));
  }, [date]);

  const handleHoursChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.value.length <= 2) {
      setInnerHours(event.target.value);
    }
  };

  const handleMinutesChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.value.length <= 2) {
      setInnerMinutes(event.target.value);
    }
  };

  const updateDate = () => {
    const updatedDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), Number(hours), Number(minutes));
    if (isValid(updatedDate)) {
      onChange(updatedDate);
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      updateDate();
    }

    if (event.currentTarget.dataset.inputId === 'minutes' && event.key === 'Tab') {
      updateDate();
    }
  };

  const handleBlur = () => {
    updateDate();
  };

  const { fieldClasses } = useFieldStyles({ hasError: false, disabled: false });

  return (
    <div onBlur={handleBlur} className={s.InputTime}>
      <span className={s.InputTime__label}>Select time</span>
      <span className={cn(s.InputTime__inputs, fieldClasses)}>
        <input
          tabIndex={1}
          onChange={handleHoursChange}
          onKeyDown={handleKeyDown}
          value={hours}
          className={s.InputTime__input}
          data-input-id="hours"
        />
        <span>:</span>
        <input
          tabIndex={2}
          onChange={handleMinutesChange}
          onKeyDown={handleKeyDown}
          value={minutes}
          className={s.InputTime__input}
          data-input-id="minutes"
        />
      </span>
    </div>
  );
};

export default InputTime;
