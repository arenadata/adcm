import { Component, EventEmitter, Input, Output } from '@angular/core';
import { BaseDirective, EventHelper } from '@app/adwp';

import { BaseEntity } from '@app/core/types';

@Component({
  selector: 'app-actions-button',
  templateUrl: './actions-button.component.html',
  styleUrls: ['./actions-button.component.scss']
})
export class ActionsButtonComponent<T extends BaseEntity> extends BaseDirective {

  EventHelper = EventHelper;

  @Input() row: T;

  @Output() onMouseenter = new EventEmitter<T>();

  getClusterData(row: any) {
    const { id, hostcomponent } = row.cluster || row;
    const { action } = row;
    return { id, hostcomponent, action };
  }

}
