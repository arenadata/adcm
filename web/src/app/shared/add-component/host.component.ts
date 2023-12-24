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
import { Component, EventEmitter, HostListener, Input, OnInit, Output } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { BehaviorSubject } from 'rxjs';
import { filter, tap } from 'rxjs/operators';
import { EventHelper } from '@app/adwp';

import { openClose } from '@app/core/animations';
import { clearEmptyField, Host, Provider } from '@app/core/types';
import { ActionsDirective } from '../components/actions/actions.directive';
import { AddService } from './add.service';
import { BaseFormDirective } from './base-form.directive';
import { DisplayMode } from './provider.component';
import { ICluster } from '@app/models/cluster';

@Component({
  selector: 'app-add-host',
  template: `
    <ng-container [formGroup]="form">
      <div class="row">
        <mat-form-field class="full-width">
          <mat-select appInfinityScroll (topScrollPoint)="getNextPageProvider()" required placeholder="Hostprovider" formControlName="provider_id">
            <mat-option value="">...</mat-option>
            <mat-option *ngFor="let p of providers$ | async" [value]="p.id">{{ p.name }}</mat-option>
          </mat-select>
          <button
            [style.fontSize.px]="24"
            matSuffix
            mat-icon-button
            [color]="expanded ? 'primary' : 'accent'"
            (click)="showHostproviderForm($event)"
            [matTooltip]="expanded ? 'Hide hostprovider creation form' : 'Create and add hostprovider'"
          >
            <mat-icon>{{ expanded ? 'clear' : 'add' }}</mat-icon>
          </button>
          <mat-error *ngIf="isError('provider_id')">
            <mat-error *ngIf="form.get('provider_id').hasError('required')">Hostprovider is required. If no hostprovider is available, add it here.</mat-error>
          </mat-error>
        </mat-form-field>
      </div>

      <div [@openClose]="expanded" class="inner">
        <app-add-provider [displayMode]="1" (cancel)="createdProvider($event)"></app-add-provider>
      </div>

      <app-input *ngIf="displayMode < 2" [form]="form" [label]="'Fully qualified domain name'" [controlName]="'fqdn'" [isRequired]="true"></app-input>

      <div class="row" *ngIf="displayMode === 2">
        <mat-form-field class="full-width">
          <input required matInput placeholder="Fully qualified domain name" formControlName="fqdn" />
          <button [style.fontSize.px]="24" [disabled]="!form.valid" matTooltip="Create host" matSuffix mat-icon-button [color]="'accent'" (click)="save()">
            <mat-icon>add_box</mat-icon>
          </button>
          <mat-error *ngIf="form.get('fqdn').hasError('required')">Fully qualified domain name is required </mat-error>
        </mat-form-field>
      </div>

      <ng-container *ngIf="displayMode === 0">
        <div class="row">
          <mat-form-field class="full-width">
            <mat-select appInfinityScroll (topScrollPoint)="getNextPageClusters()" placeholder="Cluster" formControlName="cluster_id">
              <mat-option value="">...</mat-option>
              <mat-option *ngFor="let c of clusters$ | async" [value]="c.id">{{ c.name }}</mat-option>
            </mat-select>
          </mat-form-field>
        </div>
        <app-add-controls [disabled]="!form.valid" (cancel)="onCancel()" (save)="save()"></app-add-controls>
      </ng-container>
    </ng-container>
  `,
  styles: [
    ':host {display: block; margin-top: 10px;}',
    '.inner {overflow: hidden; margin: 0 -6px;}',
    '.inner app-add-provider {padding: 10px 24px; background-color: #4e4e4e;display:block;}',
    '.row {display: flex;}',
  ],
  providers: [ActionsDirective],
  animations: [openClose],
})
export class HostComponent extends BaseFormDirective implements OnInit {
  @Input() displayMode: DisplayMode = DisplayMode.default;
  @Output() event = new EventEmitter();

  @HostListener('keyup') changes() {
    this.form.markAllAsTouched();
  }

  providers$ = new BehaviorSubject<Partial<Provider[]>>([]);
  clusters$ = new BehaviorSubject<Partial<ICluster>[]>([]);
  expanded = false;
  createdProviderId: number;

  pageCluster = 1;
  pageProvider = 1;
  limit = 10;

  constructor(private action: ActionsDirective, service: AddService, dialog: MatDialog) {
    super(service, dialog);
  }

  ngOnInit() {
    this.form = this.service.model('host').form;
    this.getProviders();
    this.getClusters();
    this.form
      .get('provider_id')
      .valueChanges.pipe(
        this.takeUntil(),
        filter((a) => a)
      )
      .subscribe((value) => this.checkAction(+value));
  }

  isError(name: string) {
    const fi = this.form.get(name);
    return fi.invalid && (fi.dirty || fi.touched);
  }

  showHostproviderForm(e: MouseEvent) {
    EventHelper.stopPropagation(e);
    this.expanded = !this.expanded;
    this.form.get('provider_id').setValue('');
  }

  checkAction(provider_id: number) {
    const ACTION_NAME = 'create_host';
    const provider = this.providers$.getValue().find((a) => a.id === provider_id);

    if (provider && provider.actions) {
      const actions = provider.actions.filter((a) => a.button === ACTION_NAME);
      if (actions && actions?.length) {
        this.action.inputData = { actions };
        this.onCancel();
        this.action.onClick();
      }
    }
  }

  save() {
    const data = clearEmptyField(this.form.value) as Host;
    if (this.displayMode !== 0) data.cluster_id = this.service.Cluster?.id;
    this.service
      .addHost(data)
      .pipe(
        this.takeUntil(),
        tap(() => this.form.controls['fqdn'].setValue(''))
      )
      .subscribe((a) => this.event.emit(`Host [ ${a.fqdn} ] has been added successfully.`));
  }

  createdProvider(id: number) {
    this.expanded = false;
    this.service
      .getList<Provider>('provider', { limit: this.limit, page: this.pageProvider - 1 })
      .pipe(tap((_) => this.form.get('provider_id').setValue(id)))
      .subscribe((list) => this.providers$.next(list));
  }

  getNextPageClusters() {
    const count = this.clusters$.getValue()?.length;
    if (count === this.pageCluster * this.limit) {
      this.pageCluster++;
      this.getClusters();
    }
  }

  getNextPageProvider() {
    const count = this.providers$.getValue()?.length;
    if (count === this.pageProvider * this.limit) {
      this.pageProvider++;
      this.getProviders();
    }
  }

  getProviders() {
    this.service
      .getList<Provider>('provider', { limit: this.limit, page: this.pageProvider - 1 })
      .pipe(tap((list) => this.form.get('provider_id').setValue(list.length === 1 ? list[0].id : '')))
      .subscribe((list) => this.providers$.next([...this.providers$.getValue(), ...list]));
    if (this.form.get('provider_id').value) this.expanded = false;
  }

  getClusters() {
    this.service
      .getList<ICluster>('cluster', { limit: this.limit, page: this.pageCluster - 1 })
      .subscribe((list) => this.clusters$.next([...this.clusters$.getValue(), ...list]));
  }
}
