import { Component, Input } from '@angular/core';
import { EventHelper } from '@adwp-ui/widgets';

import { IIssues } from '@app/models/issue';
import { IssueHelper } from '@app/helpers/issue-helper';

@Component({
  selector: 'app-actions-column',
  templateUrl: './actions-column.component.html',
  styleUrls: ['./actions-column.component.scss']
})
export class ActionsColumnComponent<T> {

  EventHelper = EventHelper;

  @Input() row: T;

  notIssue(issue: IIssues): boolean {
    return !IssueHelper.isIssue(issue);
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
