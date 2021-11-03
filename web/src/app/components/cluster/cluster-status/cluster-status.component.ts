import { Component } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';

import { ClusterEntityService } from '@app/services/cluster-entity.service';
import { ClusterStatusTree } from '@app/models/status-tree';
import { EventMessage, SocketState } from '@app/core/store';
import { StatusAbstractDirective } from '@app/abstract-directives/status.abstract.directive';

@Component({
  selector: 'app-cluster-status',
  templateUrl: '../../../templates/status-tree.html',
  styleUrls: ['../../../styles/status-tree.scss']
})
export class ClusterStatusComponent extends StatusAbstractDirective<ClusterStatusTree> {

  constructor(
    protected route: ActivatedRoute,
    protected store: Store<SocketState>,
    public entityService: ClusterEntityService,
  ) {
    super(route, store, entityService);
  }

  eventReceived(event: EventMessage) {
    let output;
    switch (event.object.type) {
      case 'hostcomponent':
        output = updateIn(fromJS(this.statusTree.value), ['chilren', 'services'], (services: any[]) =>
          services.map(service => updateIn(service, ['hc'], (components: any) =>
            components.map( (component: any) => updateIn(component, ['hosts'], (hosts: any) =>
              hosts.map((host: any) => {
                if (host.get('id') === event.object.id && component.get('id') === +event.object.details.id) {
                  return host.set('status', +event.object.details.value);
                }
                return host;
              })
            ))
          ))
        );
        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
        break;
      case 'component':
        output = updateIn(fromJS(this.statusTree.value), ['chilren', 'services'], (services: any[]) => (
          services.map(service => updateIn(service, ['hc'], (components: any) => components.map( (component: any) => {
            if (component.get('id') === event.object.id) {
              return component.set('status', +event.object.details.value);
            }
            return component;
          })))
        ));
        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
        break;
      case 'service':
        output = updateIn(fromJS(this.statusTree.value), ['chilren', 'services'], (services: any[]) => (
          services.map(service => {
            if (service.get('id') === event.object.id) {
              return service.set('status', +event.object.details.value);
            }
            return service;
          })));
        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
        break;
      case 'host':
        output = updateIn(fromJS(this.statusTree.value), ['chilren', 'hosts'], (hosts: any[]) => (
          hosts.map(host => {
            if (host.get('id') === event.object.id) {
              return host.set('status', +event.object.details.value);
            }
            return host;
          })
        ));
        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
        break;
      case 'cluster':
        output = fromJS(this.statusTree.value);
        if (output.get('id') === event.object.id) {
          output = output.set('status', +event.object.details.value);
        }
        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
        break;
    }
  }

  getEntityIdFromParams(): number {
    return +this.route.parent.snapshot.params.cluster;
  }

  prepareStatusTree(input: ClusterStatusTree): ClusterStatusTree {
    input.id = this.entityId;
    return input;
  }

}
