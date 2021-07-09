import { Pipe, PipeTransform } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

@Pipe({
  name: 'translateKeys'
})
export class TranslateKeysPipe implements PipeTransform {

  constructor(private _translate: TranslateService) {}

  transform(object: { [key: string]: any }): { [key: string]: any } {
    if (!object) {
      return {};
    }

    return Object.entries(object)
      .reduce((acc, [key, value]) => {
        return {
          ...acc,
          [this._translate.instant(key)]: value
        }
      }, {});
  }

}
