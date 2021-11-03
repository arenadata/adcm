import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';

import { StatusAbstractDirective } from '@app/abstract-directives/status.abstract.directive';
import { HostComponentStatusTree } from '@app/models/status-tree';
import { EventMessage, SocketState } from '@app/core/store';
import { ServiceComponentService } from '@app/services/service-component.service';

@Component({
  selector: 'app-service-component-status',
  templateUrl: '../../../templates/status-tree.html',
  styleUrls: ['../../../styles/status-tree.scss']
})
export class ServiceComponentStatusComponent extends StatusAbstractDirective<HostComponentStatusTree> {

  constructor(
    protected route: ActivatedRoute,
    protected store: Store<SocketState>,
    public entityService: ServiceComponentService,
  ) {
    super(route, store, entityService);
  }

  eventReceived(event: EventMessage) {
    let output;
    switch (event.object.type) {
      case 'hostcomponent':
        const componentId = this.statusTree.value.id;
        output = updateIn(fromJS(this.statusTree.value), ['hosts'], (hosts: any[]) =>
          hosts.map(host => {
            if (host.get('id') === event.object.id && componentId === +event.object.details.id) {
              return host.set('status', +event.object.details.value);
            }
            return host;
          })
        );
        this.statusTree.next(output.toJS() as any as HostComponentStatusTree);
        break;
      case 'component':
        output = fromJS(this.statusTree.value);
        if (output.get('id') === event.object.id) {
          output = output.set('status', +event.object.details.value);
        }
        this.statusTree.next(output.toJS() as any as HostComponentStatusTree);
        break;
    }
  }

  getEntityIdFromParams(): number {
    return +this.route.parent.snapshot.params.servicecomponent;
  }

}
