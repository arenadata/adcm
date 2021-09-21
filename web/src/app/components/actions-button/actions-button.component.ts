import { Component, Input } from '@angular/core';
import { EventHelper } from '@adwp-ui/widgets';

import { IssuesComponent } from '@app/components/issues/issues.component';
import { IIssues, IssueType } from '@app/models/issue';
import { IssueHelper } from '@app/helpers/issue-helper';

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

  notIssue(issue: IIssues): boolean {
    return !IssueHelper.isIssue(issue);
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
