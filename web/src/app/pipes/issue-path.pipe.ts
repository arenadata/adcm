import { Pipe, PipeTransform } from '@angular/core';
import { map } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { ServiceService } from '@app/services/service.service';
import { IssueType } from '@app/models/issue';

@Pipe({
  name: 'issuePath'
})
export class IssuePathPipe implements PipeTransform {

  constructor(
    private serviceService: ServiceService,
  ) {}

  transform(issueName: string, issueType: IssueType, id: number): Observable<string> {
    let issue = issueName;
    if (issue === 'required_import') {
      issue = 'import';
    }

    if (issueType === 'service') {
      return this.serviceService.get(id)
        .pipe(map(
          service => `/cluster/${service.cluster_id}/${issueType}/${id}/${issue}`,
        ));
    } else {
      return of(`/${issueType}/${id}/${issue}`);
    }
  }

}
