import { Directive, OnInit, ViewChild } from '@angular/core';
import { BaseDirective } from '@app/adwp';
import { BehaviorSubject } from 'rxjs';
import { Store } from '@ngrx/store';
import { ActivatedRoute, Params } from '@angular/router';
import { filter, switchMap, tap } from 'rxjs/operators';

import { StatusTreeSubject } from '../models/status-tree';
import { Folding } from '../components/status-tree/status-tree.component';
import { EventMessage, selectMessage, SocketState } from '../core/store';
import { HavingStatusTreeAbstractService } from '../abstract/having-status-tree.abstract.service';
import { AdcmEntity } from '@app/models/entity';

@Directive({
  selector: '[appStatusAbstract]',
})
export abstract class StatusAbstractDirective<StatusTreeType extends StatusTreeSubject, EntityType extends AdcmEntity> extends BaseDirective implements OnInit {

  @ViewChild('tree', { static: false }) tree: any;

  loading = false;

  entity: EntityType;
  entityId: number;
  statusTree = new BehaviorSubject<StatusTreeType>(null);

  folding: Folding;

  abstract getEntityIdFromParams(params: Params): number;

  constructor(
    protected route: ActivatedRoute,
    protected store: Store<SocketState>,
    public entityService: HavingStatusTreeAbstractService<StatusTreeType, EntityType>,
  ) {
    super();
  }

  eventReceived(event: EventMessage): void {}

  prepareListeners() {
    return this.store.pipe(
      selectMessage,
      this.takeUntil(),
      filter(event => event.event === 'change_status'),
    ).subscribe((event: EventMessage) => this.eventReceived(event));
  }

  prepareStatusTree(input: StatusTreeType): StatusTreeType {
    return input;
  }

  pipeData(): any {}

  ngOnInit(): void {
    this.route.params.pipe(
      this.takeUntil(),
      tap(() => this.loading = true),
      tap(() => this.folding = Folding.Expanded),
      tap((params) => this.entityId = this.getEntityIdFromParams(params)),
      switchMap(() => this.entityService.get(this.entityId)),
      tap(entity => this.entity = entity),
      switchMap(() => this.entityService.getStatusTree(this.entityId)),
    ).subscribe((resp) => {
      this.loading = false;
      this.statusTree.next(this.prepareStatusTree(resp));
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
