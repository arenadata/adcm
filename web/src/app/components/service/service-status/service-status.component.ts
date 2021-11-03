import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';

import { StatusAbstractDirective } from '@app/abstract-directives/status.abstract.directive';
import { EventMessage, SocketState } from '@app/core/store';
import { ServiceService } from '@app/services/service.service';
import { ServiceStatusTree } from '@app/models/status-tree';

@Component({
  selector: 'app-service-status',
  templateUrl: '../../../templates/status-tree.html',
  styleUrls: ['../../../styles/status-tree.scss']
})
export class ServiceStatusComponent extends StatusAbstractDirective<ServiceStatusTree> {

  constructor(
    protected route: ActivatedRoute,
    protected store: Store<SocketState>,
    public entityService: ServiceService,
  ) {
    super(route, store, entityService);
  }

  eventReceived(event: EventMessage) {
    let output;
    switch (event.object.type) {
      case 'hostcomponent':
        output = updateIn(fromJS(this.statusTree.value), ['hc'], (components: any[]) =>
          components.map(component => updateIn(component, ['hosts'], (hosts: any[]) =>
            hosts.map((host: any) => {
              if (host.get('id') === event.object.id && component.get('id') === +event.object.details.id) {
                return host.set('status', +event.object.details.value);
              }
              return host;
            })
          ))
        );
        this.statusTree.next(output.toJS() as any as ServiceStatusTree);
        break;
      case 'component':
        output = updateIn(fromJS(this.statusTree.value), ['hc'], (components: any[]) =>
          components.map(component => {
            if (component.get('id') === event.object.id) {
              return component.set('status', +event.object.details.value);
            }
            return component;
          })
        );
        this.statusTree.next(output.toJS() as any as ServiceStatusTree);
        break;
      case 'service':
        output = fromJS(this.statusTree.value);
        if (output.get('id') === event.object.id) {
          output = output.set('status', +event.object.details.value);
        }
        this.statusTree.next(output.toJS() as any as ServiceStatusTree);
        break;
    }
  }

  getEntityIdFromParams(): number {
    return +this.route.parent.snapshot.params.service;
  }

}
