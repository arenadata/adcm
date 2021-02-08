import { Component, Input, OnInit } from '@angular/core';

import { isIssue, Issue } from '@app/core/types';

@Component({
  selector: 'app-actions-column',
  templateUrl: './actions-column.component.html',
  styleUrls: ['./actions-column.component.scss']
})
export class ActionsColumnComponent<T> implements OnInit {

  @Input() row: T;

  constructor() { }

  ngOnInit(): void {
  }

  notIssue(issue: Issue): boolean {
    return !isIssue(issue);
  }

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
