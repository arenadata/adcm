import { Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { BaseDirective } from '@adwp-ui/widgets';
import { filter, switchMap, tap } from 'rxjs/operators';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';
import { BehaviorSubject } from 'rxjs';

import { ClusterEntityService } from '@app/services/cluster-entity.service';
import { ClusterStatusTree } from '@app/models/status-tree';
import { Folding } from '../../status-tree/status-tree.component';
import { selectMessage, SocketState } from '@app/core/store';

@Component({
  selector: 'app-cluster-status',
  templateUrl: './cluster-status.component.html',
  styleUrls: ['./cluster-status.component.scss']
})
export class ClusterStatusComponent extends BaseDirective implements OnInit {

  @ViewChild('tree', { static: false }) tree: any;

  loading = false;

  entityId: number;
  statusTree = new BehaviorSubject<ClusterStatusTree>(null);

  folding: Folding;

  constructor(
    private route: ActivatedRoute,
    private entityService: ClusterEntityService,
    private store: Store<SocketState>,
  ) {
    super();
  }

  prepareListeners() {
    return this.store.pipe(
      selectMessage,
      this.takeUntil(),
      filter(event => event.event === 'change_status'),
    ).subscribe((event) => {
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
    });
  }

  ngOnInit(): void {
    this.route.params.pipe(
      this.takeUntil(),
      tap(() => this.loading = true),
      tap(() => this.folding = Folding.Expanded),
      tap(() => this.entityId = +this.route.parent.snapshot.params.cluster),
      switchMap(() => this.entityService.getStatusTree(this.entityId)),
    ).subscribe((resp) => {
      this.loading = false;
      resp.id = this.entityId;
      this.statusTree.next(resp);
      this.prepareListeners();
    });
  }

  expandCollapseAll() {
    if (this.tree.hasCollapsed()) {
      this.tree.expandAll();
    } else {
      this.tree.collapseAll();
    }
  }

}
