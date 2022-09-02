import { Component, Input } from '@angular/core';
import { CauseType, IMPlaceholderItem, IMPlaceholderItemType } from '@app/models/concern/concern-reason';

@Component({
  selector: 'app-concern-item',
  templateUrl: './concern-item.component.html',
  styleUrls: ['./concern-item.component.scss']
})
export class ConcernItemComponent {

  IMPlaceholderItemType = IMPlaceholderItemType;

  @Input() item: string;
  @Input() cause: string;
  @Input() placeholder: IMPlaceholderItem;

  runAction() {}

  sectionByCause() {
    switch (this.cause) {
      case CauseType.HostComponent:
        return 'host_component';
      case CauseType.Config:
        return 'config';
      case CauseType.Import:
        return 'import';
      default:
        return 'main';
    }
  }

}
