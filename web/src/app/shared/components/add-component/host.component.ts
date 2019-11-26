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
import { Component, Input, OnInit } from '@angular/core';
import { clearEmptyField, Cluster, Provider } from '@app/core/types';
import { BehaviorSubject } from 'rxjs';
import { filter, tap } from 'rxjs/operators';

import { AddService } from './add.service';
import { BaseFormDirective } from './base-form.directive';
import { ActionsDirective } from '../actions/actions.directive';

@Component({
  selector: 'app-add-host',
  template: `
    <ng-container [formGroup]="form">
      <div class="row">
        <mat-form-field class="full-width">
          <mat-select required placeholder="Hostprovider" formControlName="provider_id">
            <mat-option value="">...</mat-option>
            <mat-option *ngFor="let p of providers" [value]="p.id">{{ p.name }}</mat-option>
          </mat-select>
          <button
            [style.fontSize.px]="24"
            matSuffix
            mat-icon-button
            color="accent"
            (click)="showHostproviderForm($event)"
            matTooltip="Create and add hostprovider"
          >
            <mat-icon>add_box</mat-icon>
          </button>
          <mat-error *ngIf="isError('provider_id')">
            <mat-error *ngIf="form.get('provider_id').hasError('required')">Hostprovider is required. If no hostprovider is available, add it here.</mat-error>
          </mat-error>
        </mat-form-field>
      </div>

      <div *ngIf="expanded" class="inner">
        <app-add-provider [displayMode]="1" (cancel)="createdProvider($event)"></app-add-provider>
      </div>

      <app-input [form]="form" [label]="'Fully qualified domain name'" [controlName]="'fqdn'" [isRequired]="true"></app-input>

      <div class="row" *ngIf="!noCluster">
        <mat-form-field class="full-width">
          <mat-select appInfinityScroll (topScrollPoint)="getNextPage()" placeholder="Cluster" formControlName="cluster_id">
            <mat-option value="">...</mat-option>
            <mat-option *ngFor="let c of clusters$ | async" [value]="c.id">{{ c.name }}</mat-option>
          </mat-select>
        </mat-form-field>
      </div>
      <p class="controls">
        <button mat-raised-button [disabled]="!form.valid" color="accent" (click)="save()">Save</button>
        <button mat-raised-button color="primary" (click)="onCancel()">Cancel</button>
      </p>
    </ng-container>
  `,
  styles: ['.inner {padding: 6px 8px;background-color: #4e4e4e;margin: 0 -6px;}'],
  providers: [ActionsDirective],
})
export class HostComponent extends BaseFormDirective implements OnInit {
  @Input() noCluster = false;
  providers: Provider[];
  clusters$ = new BehaviorSubject<Partial<Cluster>[]>([]);
  expanded = false;
  createdProviderId: number;

  page = 1;
  limit = 50;

  constructor(private action: ActionsDirective, public service: AddService) {
    super(service);
  }

  ngOnInit() {
    this.form = this.service.model('host').form;
    this.getProviders();
    this.getClusters();
    this.form
      .get('provider_id')
      .valueChanges.pipe(
        this.takeUntil(),
        filter(a => a),
      )
      .subscribe(value => this.checkAction(+value));
  }

  isError(name: string) {
    const fi = this.form.get(name);
    return fi.invalid && (fi.dirty || fi.touched);
  }

  showHostproviderForm(e: Event) {
    e.stopPropagation();
    this.expanded = !this.expanded;
    this.form.get('provider_id').setValue('');
  }

  checkAction(provider_id: number) {
    const ACTION_NAME = 'create_host';
    const provider = this.providers.find(a => a.id === provider_id);

    if (provider && provider.actions) {
      const actions = provider.actions.filter(a => a.button === ACTION_NAME);
      if (actions.length) {
        this.action.data = { actions };
        this.onCancel();
        this.action.onClick();
      }
    }
  }

  save() {
    const data = clearEmptyField(this.form.value);
    this.service
      .addHost(data)
      .pipe(
        this.takeUntil(),
        tap(() => this.form.controls['fqdn'].setValue('')),
      )
      .subscribe(host => this.onCancel(host, false));
  }

  createdProvider(id: number) {
    this.createdProviderId = id;
    this.expanded = false;
    this.getProviders();
  }

  getProviders() {
    this.service.getProviders().subscribe(a => {
      this.providers = a;
      this.form.get('provider_id').setValue(a.length === 1 ? a[0].id : this.createdProviderId);
    });
    if (this.form.get('provider_id').value) this.expanded = false;
  }

  getNextPage() {
    const count = this.clusters$.getValue().length;
    if (count === this.page * this.limit) {
      this.page++;
      this.getClusters();
    }
  }

  getClusters() {
    this.service.getClusters({ limit: this.limit, page: this.page - 1 }).subscribe(list => this.clusters$.next([...this.clusters$.getValue(), ...list]));
  }
}
