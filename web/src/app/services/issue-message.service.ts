import { Injectable } from '@angular/core';

@Injectable()
export class IssueMessageService {

  constructor() { }

  parse(issueMessage: string): string[] {
    let result = [];
    for (const item of issueMessage.matchAll(/(.*?)(\$\{.+?\})|(.+$)/g)) {
      if (item.length) {
        result = [ ...result, ...item.slice(1, item.length) ];
      }
    }

    return result.filter(item => !!item);
  }

}
