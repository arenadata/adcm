import { Pipe, PipeTransform } from '@angular/core';
import {CellValueType, DisabledCheckboxFunc, ValueFunc} from '../../models/list';

@Pipe({
  name: 'listCheckboxDisabled'
})
export class ListCheckboxDisabledPipe implements PipeTransform {

  transform(row: any, func: DisabledCheckboxFunc<any>): boolean {
    return func && func(row);
  }

}
