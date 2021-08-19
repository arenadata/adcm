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
import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild
} from '@angular/core';
import { EventMessage, SocketState } from '@app/core/store';
import { SocketListenerDirective } from '@app/shared/directives';
import { Store } from '@ngrx/store';
import { BehaviorSubject, Observable, of, Subscription } from 'rxjs';
import { catchError, finalize, tap } from 'rxjs/operators';

import { ConfigFieldsComponent } from '../fields/fields.component';
import { HistoryComponent } from '../tools/history.component';
import { ToolsComponent } from '../tools/tools.component';
import { IConfig } from '../types';
import { historyAnime, ISearchParam, MainService } from './main.service';
import { WorkerInstance } from '@app/core/services/cluster.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-config-form',
  templateUrl: './config.component.html',
  styleUrls: ['./config.component.scss'],
  animations: historyAnime,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [MainService]
})
export class ConfigComponent extends SocketListenerDirective implements OnChanges, OnInit {
  loadingStatus = 'Loading...';
  rawConfig = new BehaviorSubject<IConfig>(null);
  saveFlag = false;
  historyShow = false;
  isLock = false;
  isLoading = false;

  worker$: Observable<WorkerInstance>;

  @ViewChild('fls') fields: ConfigFieldsComponent;
  @ViewChild('history') historyComponent: HistoryComponent;
  @ViewChild('tools') tools: ToolsComponent;

  @Input()
  configUrl: string;

  @Input()
  isGroupConfig: boolean;

  @Output()
  event = new EventEmitter<{ name: string; data?: any }>();
  private _workerSubscription: Subscription = Subscription.EMPTY;
  private _groupsSubscription: Subscription = Subscription.EMPTY;

  constructor(
    private service: MainService,
    public cd: ChangeDetectorRef,
    socket: Store<SocketState>,
    route: ActivatedRoute,
  ) {
    super(socket);
    this.isGroupConfig = route.snapshot.data['isGroupConfig'];
    this.worker$ = service.worker$.pipe(this.takeUntil());
  }

  ngOnChanges(changes: SimpleChanges): void {
    const url = changes['configUrl'];
    const firstChange = url?.firstChange;
    if (!firstChange || !url) this.getConfigUrlFromWorker();
  }

  ngOnInit(): void {
    if (!this.configUrl) this.getConfigUrlFromWorker();
    this._getConfig(this.configUrl).subscribe();

    super.startListenSocket();
  }

  ngOnDestroy() {
    super.ngOnDestroy();
    this._workerSubscription.unsubscribe();
    this._groupsSubscription.unsubscribe();
  }

  onReady(): void {
    this.tools.isAdvanced = this.fields.isAdvanced;
    this.tools.description.setValue(this.rawConfig.value.description);
    this.filter(this.tools.filterParams);

    if (!this.isGroupConfig) {
      this.service.getHistoryList(this.configUrl, this.rawConfig.value.id).subscribe((h) => {
        this.historyComponent.compareConfig = h;
        this.tools.disabledHistory = !h.length;
        this.cd.detectChanges();
      });
    }
  };

  filter(c: ISearchParam): void {
    this.service.filterApply(this.fields.dataOptions, c);
  }

  socketListener(m: EventMessage): void {
    if (
      m.object.type === this.service.Current?.typeName &&
      m.object.id === this.service.Current.id &&
      !this.saveFlag &&
      (m.event === 'change_config' || m.event === 'change_state')
    ) {
      this.isLock = m.object.details.value === 'locked';
      this.reset();
      this._getConfig(this.configUrl).subscribe();
    }
  }

  getConfigUrlFromWorker(): void {
    this._workerSubscription.unsubscribe();
    this._workerSubscription = this.worker$
      .subscribe(_ => this.configUrl = this.service.Current?.config);
  }

  save(url: string): void {
    const form = this.fields.form;
    if (form.valid) {
      this.saveFlag = true;
      this.historyComponent.reset();
      const config = this.service.parseValue(this.fields.form.value, this.rawConfig.value.config);
      const send = {
        config,
        attr: {
          ...this.fields.attr,
          group_keys: { ...this.fields.groupsForm.value }
        },
        description: this.tools.description.value
      };
      this.isLoading = true;

      this.service.send(url, send).pipe(
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

  changeVersion(url: string, id: number): void {
    this.isLoading = true;
    this.reset();
    this.service.changeVersion(url, id).pipe(
      tap((c) => this.rawConfig.next(c)),
      finalize(() => this.isLoading = false),
      catchError(() => {
        this.loadingStatus = 'There is no config for this object.';
        return of(null);
      })
    ).subscribe();
  }

  compareVersion(ids: number[]): void {
    if (ids) this.service.compareConfig(ids, this.fields.dataOptions, this.historyComponent.compareConfig);
  }

  reset(): void {
    this.fields.form.reset();
    this.fields.dataOptions = [];
    this.historyComponent.reset();
  }


  private _getConfig(url: string): Observable<IConfig> {
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
}
