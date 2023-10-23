import React, { useEffect, useState } from 'react';
import { format } from 'date-fns';
import cn from 'classnames';
import { localDateToUtc } from '@utils/date/utcUtils';

import s from './CurrentDate.module.scss';

type FormattedDateType = {
  date: string;
  time: string;
};

const getFormattedCurrentDate = () => {
  const curDate = localDateToUtc(new Date());

  return {
    date: format(curDate, 'dd MMM yyyy'),
    time: format(curDate, 'HH:mm:ss'),
  };
};
const CurrentDate: React.FC = () => {
  const [formattedDate, setFormattedDate] = useState<FormattedDateType>(getFormattedCurrentDate());
  useEffect(() => {
    const interval = setInterval(() => setFormattedDate(getFormattedCurrentDate()), 1000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className={s.currentDate}>
      <div data-test="current-date" className={s.currentDate__item}>
        {formattedDate.date}
      </div>
      <div data-test="current-time" className={cn(s.currentDate__item, s.currentDate__item_time)}>
        {formattedDate.time}
      </div>
      <div data-test="current-time-zone" className={s.currentDate__item}>
        UTC
      </div>
    </div>
  );
};

export default CurrentDate;
