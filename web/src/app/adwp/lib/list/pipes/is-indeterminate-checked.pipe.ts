import { Pipe, PipeTransform } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';

@Pipe({
  name: 'isIndeterminateChecked',
  pure: false,
})
export class IsIndeterminateCheckedPipe implements PipeTransform {

  transform(data: MatTableDataSource<any>, modelKey: string): boolean {
    return !!data.data?.length && data.data.some(item => !!item[modelKey]) && data.data.some(item => !item[modelKey]);
  }

}
