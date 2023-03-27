import { Pipe, PipeTransform } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';

@Pipe({
  name: 'isAllChecked',
  pure: false,
})
export class IsAllCheckedPipe implements PipeTransform {

  transform(data: MatTableDataSource<any>, modelKey: string): boolean {
    return !!data.data?.length && data.data.every(item => !!item[modelKey]);
  }

}
