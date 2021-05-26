import { Pipe, PipeTransform } from '@angular/core';
import { map } from 'rxjs/operators';
import { Observable, of } from 'rxjs';

import { ServiceService } from '@app/services/service.service';
import { IssueType } from '@app/models/issue';
import { ServiceComponentService } from '@app/services/service-component.service';

@Pipe({
  name: 'issuePath'
})
export class IssuePathPipe implements PipeTransform {

  constructor(
    private serviceService: ServiceService,
    private serviceComponentService: ServiceComponentService,
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
    } else if (issueType === 'servicecomponent' || issueType === 'component') {
      return this.serviceComponentService.get(id)
        .pipe(map(
          component => `/cluster/${component.cluster_id}/service/${component.service_id}/component/${id}/${issue}`,
        ));
    } {
      return of(`/${issueType}/${id}/${issue}`);
    }
  }

}
