import { Component, Input } from '@angular/core';

import { IMPlaceholderItem, IMPlaceholderItemType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-concern-item',
  templateUrl: './concern-item.component.html',
  styleUrls: ['./concern-item.component.scss']
})
export class ConcernItemComponent {

  IMPlaceholderItemType = IMPlaceholderItemType;

  @Input() item: string;
  @Input() placeholder: IMPlaceholderItem;

  runAction() {}

}
