import Button from '@uikit/Button/Button';
import s from './DatePickerFooter.module.scss';

interface DatePickerFooterProps {
  hasError: boolean;
  onSet: () => void;
  onCancel: () => void;
}

const DatePickerFooter = ({ onSet, onCancel, hasError }: DatePickerFooterProps) => (
  <div className={s.DatePickerFooter}>
    <div className={s.SubmitSection}>
      <Button variant="secondary" onClick={onCancel}>
        Cancel
      </Button>
      <Button disabled={hasError} onClick={onSet}>
        Set
      </Button>
    </div>
  </div>
);

export default DatePickerFooter;
