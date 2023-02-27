import { Pipe, PipeTransform } from '@angular/core';
import { CellValueType, ValueFunc } from '../../models/list';

@Pipe({
  name: 'listValue'
})
export class ListValuePipe implements PipeTransform {

  transform(row: any, func: ValueFunc<any>): CellValueType {
    return func(row);
  }

}
