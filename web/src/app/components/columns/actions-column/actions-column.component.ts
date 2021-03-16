import { Component, Input } from '@angular/core';
import { EventHelper } from '@adwp-ui/widgets';

import { isIssue, Issue } from '@app/core/types';

@Component({
  selector: 'app-actions-column',
  templateUrl: './actions-column.component.html',
  styleUrls: ['./actions-column.component.scss']
})
export class ActionsColumnComponent<T> {

  EventHelper = EventHelper;

  @Input() row: T;

  notIssue(issue: Issue): boolean {
    return !isIssue(issue);
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
