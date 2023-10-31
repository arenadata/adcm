import { getDayClasses } from './CalendarCell.utils';
import { getDate, getMonth, isDateInRange } from '@utils/date/calendarUtils';

export interface CalendarDayProps {
  dayId: string;
  day: Date;
  selectedMonth: Date;
  selectedDate: Date;
  startDate?: Date;
  endDate?: Date;
  onClick: React.MouseEventHandler<HTMLButtonElement>;
}

const CalendarDay = ({ dayId, day, selectedDate, selectedMonth, onClick, startDate, endDate }: CalendarDayProps) => {
  const dayClassNames = getDayClasses({
    day,
    selectedMonth,
    selectedDate,
    startDate,
    endDate,
  });

  const isBtnDisabled = !isDateInRange(day, startDate, endDate) || getMonth(day) !== getMonth(selectedMonth);

  return (
    <button tabIndex={-1} className={dayClassNames} onClick={onClick} data-day-id={dayId} disabled={isBtnDisabled}>
      {getDate(day)}
    </button>
  );
};

export default CalendarDay;
