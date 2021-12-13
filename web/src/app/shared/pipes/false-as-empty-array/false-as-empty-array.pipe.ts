import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'falseAsEmptyArray'
})
export class FalseAsEmptyArrayPipe<T> implements PipeTransform {

  transform(value: T[] | unknown): T[] {
    return !Array.isArray(value) ? ([] as T[]) : value;
  }

}
