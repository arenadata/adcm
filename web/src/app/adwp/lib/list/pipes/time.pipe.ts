import { Pipe, PipeTransform } from '@angular/core';
import { DateTime } from 'luxon';

export type ApiTime = string;

@Pipe({
  name: 'time'
})
export class TimePipe implements PipeTransform {

  transform(time: ApiTime): string {
    return time ? DateTime.fromISO(time).toFormat('yyyy.LL.dd HH:mm:ss') : '';
  }

}
