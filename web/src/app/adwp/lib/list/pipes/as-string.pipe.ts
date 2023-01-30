import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'asString'
})
export class AsStringPipe implements PipeTransform {

  transform(value: any): string {
    return value as string;
  }

}
