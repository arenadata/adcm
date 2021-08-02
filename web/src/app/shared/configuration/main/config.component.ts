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
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { EventMessage, SocketState } from '@app/core/store';
import { SocketListenerDirective } from '@app/shared/directives';
import { Store } from '@ngrx/store';
import { BehaviorSubject, Observable, of } from 'rxjs';
import { catchError, finalize, tap } from 'rxjs/operators';

import { ConfigFieldsComponent } from '../fields/fields.component';
import { HistoryComponent } from '../tools/history.component';
import { ToolsComponent } from '../tools/tools.component';
import { IConfig } from '../types';
import { historyAnime, ISearchParam, MainService } from './main.service';
import { ClusterService } from '@app/core/services/cluster.service';

@Component({
  selector: 'app-config-form',
  templateUrl: './config.component.html',
  styleUrls: ['./config.component.scss'],
  animations: historyAnime,
  providers: [MainService],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfigComponent extends SocketListenerDirective implements OnInit {
  loadingStatus = 'Loading...';
  rawConfig = new BehaviorSubject<IConfig>(null);
  saveFlag = false;
  historyShow = false;
  isLock = false;
  isLoading = false;

  @ViewChild('fls') fields: ConfigFieldsComponent;
  @ViewChild('history') historyComponent: HistoryComponent;
  @ViewChild('tools') tools: ToolsComponent;

  private url = '';
  @Input()
  set configUrl(url: string) {
    this.url = url;
    this.getConfig().subscribe();
  }

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  get cUrl() {
    return `${this.url}current/`;
  }

  get saveUrl(): string {
    return `${this.url}history/`;
  }

  constructor(
    private service: MainService,
    public cd: ChangeDetectorRef,
    socket: Store<SocketState>,
    private clusterService: ClusterService,
  ) {
    super(socket);
  }

  ngOnInit() {
    if (!this.url) {
      this.clusterService.worker$
        .pipe(this.takeUntil())
        .subscribe(() => this.configUrl = this.service.Current?.config);
    }
    super.startListenSocket();
  }

  onReady() {
    this.tools.isAdvanced = this.fields.isAdvanced;
    this.tools.description.setValue(this.rawConfig.value.description);
    this.filter(this.tools.filterParams);
    this.service.getHistoryList(this.saveUrl, this.rawConfig.value.id).subscribe((h) => {
      this.historyComponent.compareConfig = h;
      this.tools.disabledHistory = !h.length;
      this.cd.detectChanges();
    });
  }

  filter(c: ISearchParam) {
    this.service.filterApply(this.fields.dataOptions, c);
  }

  socketListener(m: EventMessage) {
    if (
      m.object.type === this.service.Current?.typeName &&
      m.object.id === this.service.Current.id &&
      !this.saveFlag &&
      (m.event === 'change_config' || m.event === 'change_state')
    ) {
      this.isLock = m.object.details.value === 'locked';
      this.reset();
      this.getConfig().subscribe();
    }
  }

  getConfig(url = this.cUrl): Observable<IConfig> {
    this.isLoading = true;
    return this.service.getConfig(url).pipe(
      tap((c) => this.rawConfig.next(c)),
      finalize(() => this.isLoading = false),
      catchError(() => {
        this.loadingStatus = 'There is no config for this object.';
        return of(null);
      })
    );
  }

  save() {
    const form = this.fields.form;
    if (form.valid) {
      this.saveFlag = true;
      this.historyComponent.reset();
      const config = this.service.parseValue(this.fields.form.value, this.rawConfig.value.config);
      const send = { config, attr: this.fields.attr, description: this.tools.description.value };
      this.isLoading = true;
      this.service.send(this.saveUrl, send).pipe(
        tap((c) => {
          this.saveFlag = false;
          this.rawConfig.next(c);
          this.cd.detectChanges();
          this.event.emit({ name: 'send', data: this.fields });
        }),
        finalize(() => this.isLoading = false),
      ).subscribe();
    } else {
      Object.keys(form.controls).forEach((controlName) => form.controls[controlName].markAsTouched());
    }
  }

  changeVersion(id: number) {
    this.reset();
    this.getConfig(`${this.saveUrl}${id}/`).subscribe();
  }

  compareVersion(ids: number[]) {
    if (ids) this.service.compareConfig(ids, this.fields.dataOptions, this.historyComponent.compareConfig);
  }

  reset() {
    this.fields.form.reset();
    this.fields.dataOptions = [];
    this.historyComponent.reset();
  }
}
