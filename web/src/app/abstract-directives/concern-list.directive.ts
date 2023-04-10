import { Directive, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatDialog } from '@angular/material/dialog';
import { Store } from '@ngrx/store';

import { AdwpListDirective } from './adwp-list.directive';
import { ListService } from '../shared/components/list/list.service';
import { SocketState } from '../core/store';
import { ConcernService } from '../services/concern.service';
import { ConcernEventType } from '../models/concern/concern-reason';

@Directive({
  selector: '[appConcernList]',
})
export abstract class ConcernListDirective<T> extends AdwpListDirective<T> implements OnInit {

  abstract eventTypes: ConcernEventType[];

  constructor(
    protected service: ListService,
    protected store: Store<SocketState>,
    public route: ActivatedRoute,
    public router: Router,
    public dialog: MatDialog,
    protected concernService: ConcernService,
  ) {
    super(service, store, route, router, dialog);
  }

  ngOnInit() {
    super.ngOnInit();

    this.concernService.events({ types: this.eventTypes })
      .pipe(this.takeUntil())
      .subscribe(resp => {
        if (resp.event !== 'delete') {
          const row = this.findRow(resp.object.id);
          if (row) {
            this.rewriteRow(row);
          }
        }
      });
  }

}
