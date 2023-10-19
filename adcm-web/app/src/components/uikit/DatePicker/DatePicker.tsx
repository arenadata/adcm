import { useRef, useState } from 'react';
import CalendarPicker from '@uikit/DatePicker/components/CalendarPicker/CalendarPicker';
import Popover from '@uikit/Popover/Popover';
import Input from '@uikit/Input/Input';
import PopoverPanelDefault from '@uikit/Popover/PopoverPanelDefault/PopoverPanelDefault';
import { FieldProps } from '@uikit/Field/Field.types';
import { SubmitDatePickerHandler } from '@uikit/DatePicker/DatePicker.types';
import { formatDate } from '@uikit/DatePicker/DatePicker.utils';
import s from '@uikit/DatePicker/DatePicker.module.scss';
import cn from 'classnames';

export interface DatePickerProps extends FieldProps {
  onSubmit: SubmitDatePickerHandler;
  placeholder?: string;
  minDate?: Date;
  maxDate?: Date;
  value?: Date;
  className?: string;
  size?: 'small' | 'medium';
}

const DatePicker = ({
  placeholder,
  onSubmit,
  minDate,
  maxDate,
  disabled = false,
  value,
  className,
  variant,
  size,
  hasError = false,
}: DatePickerProps) => {
  const [open, setOpen] = useState(false);
  const reference = useRef(null);

  const handleToggle = () => {
    !disabled && setOpen((isOpen) => !isOpen);
  };

  const handleSet = (date?: Date) => {
    if (!hasError) {
      onSubmit && onSubmit(date);
      handleToggle();
    }
  };

  const inputClassNames = cn(s.datePicker__input, className, {
    [s.datePicker_small]: size === 'small',
    'is-active': open,
  });

  return (
    <>
      <Input
        ref={reference}
        value={formatDate(value)}
        readOnly
        disabled={disabled}
        className={inputClassNames}
        placeholder={placeholder}
        variant={variant}
        hasError={hasError}
        onClick={handleToggle}
      />
      <Popover
        triggerRef={reference}
        isOpen={open}
        onOpenChange={setOpen}
        placement="bottom"
        offset={8}
        dependencyWidth="parent"
      >
        <PopoverPanelDefault className={s.datePicker__panel} data-test="data-picker-popover">
          <CalendarPicker
            onSet={handleSet}
            onCancel={handleToggle}
            minDate={minDate}
            maxDate={maxDate}
            value={value}
            hasError={hasError}
          />
        </PopoverPanelDefault>
      </Popover>
    </>
  );
};

export default DatePicker;
