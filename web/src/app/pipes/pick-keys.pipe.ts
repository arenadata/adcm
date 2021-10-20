import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'pickKeys'
})
export class PickKeysPipe implements PipeTransform {

  transform(object: { [key: string]: any }, keys: string[]): { [key: string]: any } {
    return keys.reduce((result, key) => ({ ...result, [key]: object[key] }), {});
  }

}
