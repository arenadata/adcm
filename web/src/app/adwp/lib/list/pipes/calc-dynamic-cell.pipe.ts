import { Pipe, PipeTransform } from '@angular/core';

import { DynamicColumnFunc, ICell } from '../../models/list';

@Pipe({
  name: 'calcDynamicCell'
})
export class CalcDynamicCellPipe implements PipeTransform {

  transform(row: any, func: DynamicColumnFunc<any>): ICell {
    return func(row);
  }

}
