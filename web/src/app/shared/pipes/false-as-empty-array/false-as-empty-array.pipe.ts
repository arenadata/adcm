import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'falseAsEmptyArray'
})
export class FalseAsEmptyArrayPipe implements PipeTransform {

  transform(value: any): any[] {
    return !Array.isArray(value) ? [] : value;
  }

}
