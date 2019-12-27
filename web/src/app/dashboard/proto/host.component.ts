// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Component, EventEmitter, OnDestroy, OnInit } from '@angular/core';
import { ApiService } from '@app/core/api';
import { IButton, Widget } from '@app/core/types';
import { Host } from '@app/core/types/api';
import { DynamicComponent, DynamicEvent } from '@app/shared/directives/dynamic.directive';
import { environment } from '@env/environment';
import { Observable, of, Subject } from 'rxjs';
import { concatAll, filter, map, switchMap, takeUntil, tap } from 'rxjs/operators';

import { ChannelService } from '../channel.service';

@Component({
  selector: 'app-host-widget',
  template: `<mat-accordion>
    <mat-expansion-panel [expanded]="!expanded" *ngIf="(host$ | async) as list">     
      <mat-nav-list>
      <mat-list-item *ngFor="let host of list">
        <span>{{ host.fqdn | uppercase }}</span>
      </mat-list-item>    
      </mat-nav-list>
      <i *ngIf="list.length===0">Add a host.</i>
    </mat-expansion-panel>
    <mat-expansion-panel [expanded]="expanded">
    </mat-expansion-panel>
  </mat-accordion>
  
  <button mat-icon-button *ngFor="let button of model.actions" 
    matTooltip="{{ button.title }}" 
    [color]="button.color" 
    (click)="action(button)">
      <mat-icon>{{ button.icon }}</mat-icon>
  </button>`,
})
export class HostComponent implements DynamicComponent, OnInit, OnDestroy {
  event = new EventEmitter<DynamicEvent>();
  model?: Widget;

  public expanded = false;
  host$: Observable<Host[]>;
  url: string;

  // @ViewChild('form')
  // form: AddHostComponent;

  destroy$ = new Subject();

  constructor(private api: ApiService, private channel: ChannelService) {
    this.channel.stream$
      .pipe(
        takeUntil(this.destroy$),
        filter(data => data.cmd === 'stack_added' || data.cmd === 'cluster_added')
      )
      .subscribe(data => {
        // if (data.cmd === 'stack_added') this.form.options$ = null;
        // if (data.cmd === 'cluster_added') this.form.clusters$ = null;
      });
  }

  ngOnInit() {
    this.refresh();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  refresh() {
    this.host$ = this.api.root.pipe(
      tap(root => (this.url = root.host)),
      switchMap(root => this.api.get<Host[]>(root.host))
    );
  }

  add(value) {
    const link = `${environment.apiRoot}cluster/${value.cluster_id}/host/`;
    const a$ = this.api.post<Host>(this.url, value);
    const b$ = a$.pipe(map(host => (value.cluster_id ? this.api.post(link, { id: host.id }) : of(true))));

    // b$.pipe(
    //   concatAll(),
    //   tap(() => (this.model.actions.find(a => a.name === 'addHost').title = 'Add host')),
    //   tap(() => (this.expanded = false))
    // ).subscribe(() => this.refresh());
  }

  action(b: IButton) {
    this.event.emit({ name: b.name, data: b });

    if (b.name === 'addHost') {
      this.expanded = !this.expanded;
      this.model.actions.find(a => a.name === 'addHost').title = this.expanded ? 'Cancel' : 'Add host';
    }
  }
}
