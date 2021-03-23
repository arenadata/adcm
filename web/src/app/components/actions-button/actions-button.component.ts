import { Component, Input } from '@angular/core';
import { EventHelper } from '@adwp-ui/widgets';

import { isIssue, Issue } from '@app/core/types';
import { IssuesComponent } from '@app/components/issues/issues.component';
import { IssueType } from '@app/models/issue';

@Component({
  selector: 'app-actions-button',
  templateUrl: './actions-button.component.html',
  styleUrls: ['./actions-button.component.scss']
})
export class ActionsButtonComponent<T> {

  IssuesComponent = IssuesComponent;
  EventHelper = EventHelper;

  @Input() row: T;
  @Input() issueType: IssueType;

  notIssue(issue: Issue): boolean {
    return !isIssue(issue);
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
