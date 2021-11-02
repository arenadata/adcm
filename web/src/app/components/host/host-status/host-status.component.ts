import { Component, OnInit, ViewChild } from '@angular/core';
import { filter, switchMap, tap } from 'rxjs/operators';
import { BaseDirective } from '@adwp-ui/widgets';
import { ActivatedRoute } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { Store } from '@ngrx/store';
import { fromJS, updateIn } from 'immutable';

import { Folding } from '@app/components/status-tree/status-tree.component';
import { selectMessage, SocketState } from '@app/core/store';
import { HostStatusTree } from '@app/models/status-tree';
import { HostService } from '@app/services/host.service';

@Component({
  selector: 'app-host-status',
  templateUrl: './host-status.component.html',
  styleUrls: ['./host-status.component.scss']
})
export class HostStatusComponent extends BaseDirective implements OnInit {

  @ViewChild('tree', { static: false }) tree: any;

  loading = false;

  entityId: number;
  statusTree = new BehaviorSubject<HostStatusTree>(null);

  folding: Folding;

  constructor(
    private route: ActivatedRoute,
    private entityService: HostService,
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
            if (component.get('id') === event.object.id && hostId === +event.object.details.id) {
              return component.set('status', +event.object.details.value);
            }
            return component;
          }));
          this.statusTree.next(output.toJS() as any as HostStatusTree);
          break;
      }
    });
  }

  ngOnInit(): void {
    this.route.params.pipe(
      this.takeUntil(),
      tap(() => this.loading = true),
      tap(() => this.folding = Folding.Expanded),
      tap(() => this.entityId = +this.route.parent.snapshot.params.host),
      switchMap(() => this.entityService.getStatusTree(this.entityId)),
    ).subscribe((resp) => {
      this.loading = false;
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
