import { Pipe, PipeTransform } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import {DisabledCheckboxFunc} from "../../models/list";

@Pipe({
  name: 'isMainCheckboxDisabled',
  pure: false,
})
export class IsMainCheckboxDisabledPipe implements PipeTransform {

  transform(data: MatTableDataSource<any>, isDisabled: DisabledCheckboxFunc<any>): boolean {
    return !data.data?.length || data.data.every(item => isDisabled && isDisabled(item));
  }

}
