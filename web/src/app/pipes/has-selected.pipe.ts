import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'hasSelected',
  // tslint:disable-next-line:no-pipe-impure
  pure: false,
})
export class HasSelectedPipe implements PipeTransform {

  transform(dataSource: { results: any[]; count: number; }): boolean {
    return !!dataSource?.results?.filter((row) => (row as any).checked).length;
  }

}
