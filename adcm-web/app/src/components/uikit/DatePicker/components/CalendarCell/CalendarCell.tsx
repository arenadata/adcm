import { getDayClasses } from './CalendarCell.utils';
import { getDate } from '@utils/date/calendarUtils';

export interface CalendarDayProps {
  dayId: string;
  day: Date;
  selectedMonth: Date;
  selectedDate: Date;
  startDate?: Date;
  endDate?: Date;
  onClick: React.MouseEventHandler<HTMLButtonElement>;
}

const CalendarDay = ({ dayId, day, selectedDate, selectedMonth, onClick }: CalendarDayProps) => {
  const dayClassNames = getDayClasses({
    day,
    selectedMonth,
    selectedDate,
  });

  return (
    <button tabIndex={-1} className={dayClassNames} onClick={onClick} data-day-id={dayId}>
      {getDate(day)}
    </button>
  );
};

export default CalendarDay;
