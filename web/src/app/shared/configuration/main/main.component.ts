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
import { animate, state, style, transition, trigger } from '@angular/animations';
import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input, OnInit, ViewChild } from '@angular/core';
import { ClusterService } from '@app/core';
import { ApiService } from '@app/core/api';
import { EventMessage, SocketState } from '@app/core/store';
import { IConfig, parseValueConfig } from '@app/core/types';
import { SocketListener } from '@app/shared/directives';
import { Store } from '@ngrx/store';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

import { IToolsEvent } from '../field.service';
import { FieldComponent } from '../field/field.component';
import { ConfigFieldsComponent } from '../fields/fields.component';
import { HistoryComponent } from '../tools/history.component';
import { ToolsComponent } from '../tools/tools.component';

@Component({
  selector: 'app-config-form',
  templateUrl: './main.component.html',
  styleUrls: ['./main.component.scss'],
  animations: [
    trigger('history', [
      state('hide', style({ top: '130px' })),
      state('show', style({ top: '200px' })),
      state('hideTools', style({ opacity: 0 })),
      state('showTools', style({ opacity: 0.8 })),
      transition('hideTools => showTools', animate('.5s .3s ease-in')),
      transition('showTools => hideTools', animate('.2s ease-out')),
      transition('hide <=> show', animate('.3s')),
    ]),
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConfigComponent extends SocketListener implements OnInit {
  loadingStatus = 'Loading...';
  config$: Observable<IConfig>;
  rawConfig: IConfig;

  saveFlag = false;
  historyShow = false;

  private _url = '';

  @ViewChild('fields', { static: false }) fields: ConfigFieldsComponent;
  @ViewChild('history', { static: false }) historyComponent: HistoryComponent;
  @ViewChild('tools', {static: false}) tools: ToolsComponent;

  @Input()
  set configUrl(url: string) {
    this._url = url;
    this.config$ = this.getConfig();
  }

  get historyUrl(): string {
    return `${this._url}history/`;
  }

  constructor(private api: ApiService, private current: ClusterService, socket: Store<SocketState>, private cdRef: ChangeDetectorRef) {
    super(socket);
  }

  ngOnInit() {
    if (!this._url && this.current.Current) {
      this.configUrl = this.current.Current.config;
    }
   
    super.startListenSocket();
  }

  toolsEvent(toolsEvent: IToolsEvent) {
    this[toolsEvent.name](toolsEvent.conditions);
  }

  get formValid() {
    return this.fields ? this.fields.form.valid : false;
  }

  history(flag: boolean) {
    this.historyShow = flag;
  }

  filter(c: {advanced: boolean, search: string}) {
    const fields = this.fields.fields.filter(a => a.options.name !== '__main_info').filter(a => a.options.type !== 'group');

    this.applyFields(fields, c);

    this.fields.panels
      .filter(p => p.ui_options && p.ui_options.advanced && !p.ui_options.invisible)
      .map(p => {
        p.hidden = !c.advanced;
        /**
         * TODO:
         * this.fields.fields
         * this.fields.panels.fields
         * this.fields.groups.fields
         */
        if (p.options.length === 1 && p.options[0].ui_options && !p.options[0].ui_options.invisible) {
          p.options[0].hidden = !c.advanced;
        }
        return p;
      });

    this.fields.groups.forEach(g => this.applyFields(g.fields.toArray(), c));
  }

  applyFields(fields: FieldComponent[], co: {advanced: boolean, search: string}) {
    fields
      .filter(a => !a.options.ui_options || !a.options.ui_options.invisible)
      .map(c => {
        c.options.hidden = !(c.options.label.includes(co.search) || JSON.stringify(c.options.value).includes(co.search));
        c.cdetector.markForCheck();
        return c;
      })
      .filter(a => !a.options.hidden && a.options.ui_options && a.options.ui_options.advanced)
      .map(a => {
        a.options.hidden = !co.advanced;
        a.cdetector.markForCheck();
        return a;
      });
  }

  socketListener(m: EventMessage) {
    if (
      this.current.Current &&
      m.event === 'change_config' &&
      m.object.type === this.current.Current.typeName &&
      m.object.id === this.current.Current.id &&
      !this.saveFlag
    )
      this.config$ = this.getConfig();
  }

  getConfig() {
    return this.api.get<IConfig>(`${this._url}current/`).pipe(
      tap(c => {
        this.rawConfig = c;
        if (!c || !Object.keys(c).length || !c.config.length) this.loadingStatus = 'No configs.';
      }),
      catchError(() => {
        this.loadingStatus = 'Loading error.';
        return of(null);
      })
    );
  }

  save() {
    const form = this.fields.form;
    if (form.valid) {
      this.saveFlag = true;
      const config = parseValueConfig(this.rawConfig.config.filter(a => !a.read_only && a.type !== 'group'), form.value),
        attr = this.rawConfig.attr,
        description = this.tools.descriptionFormControl.value;

      const send = { config };
      if (attr) send['attr'] = attr;
      if (description) send['description'] = description;

      this.api
        .post<IConfig>(this.historyUrl, send)
        .pipe(this.takeUntil())
        .subscribe(c => {
          this.saveFlag = false;
          this.historyComponent.versionID = c.id;
          this.historyComponent.getData();
          this.cdRef.detectChanges();
        });
    } else {
      Object.keys(form.controls).forEach(controlName => form.controls[controlName].markAsTouched());
    }
  }

  changeVersion(a: { id: number }) {
    this.config$ = this.api.get<IConfig>(`${this.historyUrl}${a.id}/`);
  }

}
