import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'issueMessagePlaceholder'
})
export class IssueMessagePlaceholderPipe implements PipeTransform {

  transform(value: string): string {
    return value.replace(/(\$\{)|(\})/g, '');
  }

}
