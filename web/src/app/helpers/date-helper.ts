import { DateTime } from 'luxon';

export class DateHelper {

  static short(date: string) {
    return DateTime.fromISO(date).setLocale('en').toFormat('FF');
  }

}
