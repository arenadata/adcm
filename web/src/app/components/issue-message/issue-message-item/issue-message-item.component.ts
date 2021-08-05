import { Component, Input } from '@angular/core';

import { IMPlaceholderItem, IMPlaceholderItemType } from '@app/models/issue-message';

@Component({
  selector: 'app-issue-message-item',
  templateUrl: './issue-message-item.component.html',
  styleUrls: ['./issue-message-item.component.scss']
})
export class IssueMessageItemComponent {

  IMPlaceholderItemType = IMPlaceholderItemType;

  @Input() item: string;
  @Input() placeholder: IMPlaceholderItem;

  runAction() {}

}
