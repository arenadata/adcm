import { Pipe, PipeTransform } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

@Pipe({
  name: 'toDataSource'
})
export class ToDataSourcePipe implements PipeTransform {

  constructor(private _translate: TranslateService) {}

  transform(model: { [key: string]: any }): { results: any[]; count: number; } {
    if (!model) {
      return { results: [], count: 0 };
    }

    const results = Object.entries(model)
      .reduce((acc, [key, value]) => {
        return [...acc, { key: this._translate.instant(key), value }];
      }, []);

    return { results, count: 0 };
  }

}
