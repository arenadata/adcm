import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { BaseDirective } from '@adwp-ui/widgets';
import { filter, switchMap } from 'rxjs/operators';
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

  Folding = Folding;

  statusTree = new BehaviorSubject<ClusterStatusTree>(null);

  folding: Folding;

  constructor(
    private route: ActivatedRoute,
    private clusterEntityService: ClusterEntityService,
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
      if (event.object.type === 'component') {
        const output = updateIn(fromJS(this.statusTree.value), ['chilren', 'services'], (services: any[]) => (
          services.map(service => updateIn(service, ['hc'], (components: any) => components.map( (component: any) => {
            if (component.get('id') === event.object.id) {
              return component.set('status', +event.object.details.value);
            }
            return component;
          })))
        ));

        this.statusTree.next(output.toJS() as any as ClusterStatusTree);
      }
    });
  }

  ngOnInit(): void {
    this.route.params.pipe(
      this.takeUntil(),
      switchMap(() => this.clusterEntityService.getStatusTree(+this.route.parent.snapshot.params.cluster)),
    ).subscribe((resp) => {
      this.statusTree.next(resp);
      this.prepareListeners();
    });
  }

}
