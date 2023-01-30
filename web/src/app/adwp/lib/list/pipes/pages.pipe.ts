import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'pages'
})
export class PagesPipe implements PipeTransform {

  transform(numberOfPages: number): Array<number> {
    const ownPages = [];
    for (let index = 1; index <= numberOfPages; index++) {
      ownPages.push(index);
    }
    return ownPages;
  }

}
