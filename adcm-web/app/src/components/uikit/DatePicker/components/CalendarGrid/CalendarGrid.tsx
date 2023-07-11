import CalendarCell from '../CalendarCell/CalendarCell';
import { CalendarMap, ChangeMonthHandler, ChangeDateHandler } from '@uikit/DatePicker/DatePicker.types';
import s from './CalendarGrid.module.scss';

interface CalendarGridProps {
  calendarMap: CalendarMap;
  selectedDate: Date;
  selectedMonth: Date;
  minDate?: Date;
  maxDate?: Date;
  onMonthChange: ChangeMonthHandler;
  onDateClick: ChangeDateHandler;
}

const CalendarGrid = ({
  calendarMap,
  selectedDate,
  selectedMonth,
  minDate,
  maxDate,
  onDateClick,
}: CalendarGridProps) => {
  const daysIds: Record<string, Date> = {};

  const handleDayClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (e.currentTarget.dataset.dayId) {
      const date: Date = daysIds[e.currentTarget.dataset.dayId];
      onDateClick(date);
    }
  };

  return (
    <div className={s.calendarGrid}>
      {calendarMap.map((week, index) =>
        week.map((day) => {
          const dayId = `${index}${day}`;
          daysIds[dayId] = day;

          return (
            <CalendarCell
              dayId={dayId}
              key={dayId}
              day={day}
              selectedDate={selectedDate}
              selectedMonth={selectedMonth}
              startDate={minDate}
              endDate={maxDate}
              onClick={handleDayClick}
            />
          );
        }),
      )}
    </div>
  );
};

export default CalendarGrid;
