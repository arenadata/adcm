import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';

import { EventMessage, SocketState } from '@app/core/store';
import { HostStatusTree } from '@app/models/status-tree';
import { HostService } from '@app/services/host.service';
import { StatusAbstractDirective } from '@app/abstract-directives/status.abstract.directive';

@Component({
  selector: 'app-host-status',
  templateUrl: '../../../templates/status-tree.html',
  styleUrls: ['../../../styles/status-tree.scss']
})
export class HostStatusComponent extends StatusAbstractDirective<HostStatusTree> {

  constructor(
    protected route: ActivatedRoute,
    protected store: Store<SocketState>,
    public entityService: HostService,
  ) {
    super(route, store, entityService);
  }

  eventReceived(event: EventMessage) {
    let output;
    switch (event.object.type) {
      case 'host':
        output = fromJS(this.statusTree.value);
        if (output.get('id') === event.object.id) {
          output = output.set('status', +event.object.details.value);
        }
        this.statusTree.next(output.toJS() as any as HostStatusTree);
        break;
      case 'hostcomponent':
        output = fromJS(this.statusTree.value);
        const hostId = output.get('id');
        output = updateIn(output, ['hc'], (components: any[]) => components.map((component: any) => {
          if (component.get('id') === +event.object.details.id && hostId === event.object.id) {
            return component.set('status', +event.object.details.value);
          }
          return component;
        }));
        this.statusTree.next(output.toJS() as any as HostStatusTree);
        break;
    }
  }

  getEntityIdFromParams(): number {
    return +this.route.parent.snapshot.params.host;
  }

}
