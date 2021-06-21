import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'toDataSource'
})
export class ToDataSourcePipe implements PipeTransform {

  transform(model: { [key: string]: any }): { results: any[]; count: number; } {
    if (!model) {
      return { results: [], count: 0 };
    }

    const results = Object.entries(model)
      .reduce((acc, [key, value]) => [...acc, { key, value }], []);

    return { results, count: 0 };

  }

}
