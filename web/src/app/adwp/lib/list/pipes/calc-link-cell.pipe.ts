import { Pipe, PipeTransform } from '@angular/core';

import { UrlColumnFunc } from '../../models/list';

@Pipe({
  name: 'calcLinkCell'
})
export class CalcLinkCellPipe implements PipeTransform {

  transform(row: any, func: UrlColumnFunc<any>): string {
    return func(row);
  }

}
