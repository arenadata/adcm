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
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { ConfigFieldsComponent } from '../fields/fields.component';
import { HistoryComponent } from '../tools/history.component';
import { ToolsComponent } from '../tools/tools.component';
import { IConfig } from '../types';
import { historyAnime, ISearchParam, MainService } from './main.service';

@Component({
  selector: 'app-config-form',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
  animations: historyAnime,
  providers: [MainService],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfigComponent extends SocketListenerDirective implements OnInit {
  loadingStatus = 'Loading...';
  rawConfig: IConfig;
  saveFlag = false;
  historyShow = false;
  isLock = false;
  config$: Observable<IConfig>;

  @ViewChild('fls') fields: ConfigFieldsComponent;
  @ViewChild('history') historyComponent: HistoryComponent;
  @ViewChild('tools') tools: ToolsComponent;

  private url = '';
  @Input()
  set configUrl(url: string) {
    this.url = url;
    this.config$ = this.getConfig();
  }

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();

  get cUrl() {
    return `${this.url}current/`;
  }

  get saveUrl(): string {
    return `${this.url}history/`;
  }

  constructor(private service: MainService, public cd: ChangeDetectorRef, socket: Store<SocketState>) {
    super(socket);
  }

  ngOnInit() {
    if (!this.url) this.configUrl = this.service.Current?.config;
    super.startListenSocket();
  }

  onReady() {
    this.tools.isAdvanced = this.fields.isAdvanced;
    this.tools.description.setValue(this.rawConfig.description);
    this.filter(this.tools.filterParams);
    this.service.getHistoryList(this.saveUrl, this.rawConfig.id).subscribe((h) => {
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
      this.config$ = this.getConfig();
    }
  }

  getConfig(url = this.cUrl): Observable<IConfig> {
    return this.service.getConfig(url).pipe(
      tap((c) => (this.rawConfig = c)),
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
      const config = this.service.parseValue(this.fields.form.value, this.rawConfig.config);
      const send = { config, attr: this.fields.attr, description: this.tools.description.value };
      this.config$ = this.service.send(this.saveUrl, send).pipe(
        tap((c) => {
          this.saveFlag = false;
          this.rawConfig = c;
          this.cd.detectChanges();
          this.event.emit({ name: 'send', data: this.fields });
        })
      );
    } else {
      Object.keys(form.controls).forEach((controlName) => form.controls[controlName].markAsTouched());
    }
  }

  changeVersion(id: number) {
    this.reset();
    this.config$ = this.getConfig(`${this.saveUrl}${id}/`);
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
