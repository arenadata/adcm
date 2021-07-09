import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'pickKeys'
})
export class PickKeysPipe implements PipeTransform {

  transform(model: { [key: string]: any }, keys: string[]): { [key: string]: any } {
    return Object.keys(model)
      .filter(key => keys.indexOf(key) >= 0)
      .reduce((obj, key) => (obj[key] = model[key], obj), {});
  }

}
