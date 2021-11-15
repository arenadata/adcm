import { Pipe, PipeTransform } from '@angular/core';
import { BaseEntity } from '@app/core/types';

@Pipe({
  name: 'concernMenuItem'
})
export class ConcernMenuItemPipe implements PipeTransform {

  transform(value: BaseEntity, cause: string): boolean {
    const concerns = value && value.concerns;
    if (!(concerns && concerns.length)) return false;

    return !!concerns.filter((c) => c.cause === cause).length;
  }

}
