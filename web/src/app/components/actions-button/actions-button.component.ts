import { Component, Input } from '@angular/core';
import { BaseDirective, EventHelper } from '@adwp-ui/widgets';

import { IssuesComponent } from '@app/components/issues/issues.component';
import { IssueType } from '@app/models/issue';
import { BaseEntity } from '@app/core/types';

@Component({
  selector: 'app-actions-button',
  templateUrl: './actions-button.component.html',
  styleUrls: ['./actions-button.component.scss']
})
export class ActionsButtonComponent<T extends BaseEntity> extends BaseDirective {

  IssuesComponent = IssuesComponent;
  EventHelper = EventHelper;

  @Input() row: T;
  @Input() issueType: IssueType;

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
