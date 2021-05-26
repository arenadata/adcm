import { Component, Input } from '@angular/core';

import { PopoverContentDirective } from '@app/abstract-directives/popover-content.directive';
import { PopoverInput } from '@app/directives/popover.directive';
import { IssueEntity, IssueType } from '@app/models/issue';

interface IssuesInput extends PopoverInput {
  row: IssueEntity;
  issueType: IssueType;
}

@Component({
  selector: 'app-issues',
  template: `
    <div>{{ intro }}</div>
    <div *ngFor="let name of data?.row?.issue | keys">
      <ng-container *ngIf="data.row.issue[name] | isArray; else item_tpl">
        <div class="item-step">
          {{ name }}:
          <span *ngFor="let issue of data.row.issue[name]">
            <b>{{ issue.name }}</b>
            <app-issues [data]="{ row: issue, issueType: name }" intro=""></app-issues>
          </span>
        </div>
      </ng-container>
      <ng-template #item_tpl>
        <a class="issue" [routerLink]="(name | issuePath : data.issueType : data.row.id) | async">{{ IssueNames[name] || name }}</a>
      </ng-template>
    </div>
  `,
  styles: [`
    :host{
      cursor: auto;
    }
    a, .item-step {
      display: block;
      margin: 6px 0 8px 12px;
      white-space: nowrap;
    }
    a.issue {
      color: #90caf9 !important;
      text-decoration: none;
      cursor: pointer;
    }
    a.issue:hover {
      color: #64b5f6 !important;
      text-decoration: underline;
    }
  `],
})
export class IssuesComponent extends PopoverContentDirective {

  @Input() intro = 'Issues in:';

  readonly IssueNames = {
    config: 'Configuration',
    host_component: 'Host - Components',
    required_service: 'Required a service',
    required_import: 'Required a import',
  };

  @Input() data: IssuesInput;

}
