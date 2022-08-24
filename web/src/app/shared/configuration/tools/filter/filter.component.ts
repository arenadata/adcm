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
import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { BaseDirective } from "../../../directives";

export interface IFilter {
  id: number,
  name: string,
  display_name: string,
  filter_field: string,
  options: IFilterOption[],
  active?: boolean,
}

export interface IFilterOption {
  id: number,
  name: string,
  display_name: string,
  value: any,
}

@Component({
  selector: 'app-filter',
  template: `
    <div class="filter-container">
      <div class="filter-toggle-button" [matMenuTriggerFor]="list.menu">
        <mat-icon>filter_list</mat-icon>
        <filter-list #list [filters]="availableFilters" (toggleFilter)="toggleFilters($event)"></filter-list>
      </div>

      <form [formGroup]="filterForm">
        <ng-container *ngIf="filterList.length > 0">
          <ng-container *ngFor="let filter of filters">
            <mat-form-field class="filter-field">
              <mat-select placeholder="{{ filter.display_name }}" formControlName="{{ filter.filter_field }}"
                          (selectionChange)="applyFilters()">
                <mat-option *ngFor="let p of filter.options" [value]="p.name">{{ p.display_name }}</mat-option>
              </mat-select>
              <button mat-button matSuffix mat-icon-button aria-label="Clear"
                      *ngIf="this.filterForm?.getRawValue()[filter.filter_field]"
                      (click)="clear(filter.filter_field, $event)">
                <mat-icon>refresh</mat-icon>
              </button>
              <button mat-button matSuffix mat-icon-button aria-label="Remove"
                      (click)="removeFilter(filter, $event)">
                <mat-icon>close</mat-icon>
              </button>
            </mat-form-field>
          </ng-container>
        </ng-container>
      </form>
    </div>
  `,
  styleUrls: ['./filter.component.scss'],
})
export class FilterComponent extends BaseDirective implements OnInit, OnDestroy {
  filterForm = new FormGroup({});
  availableFilters: any[];
  activeFilters: number[] = [];
  preFilteredData: any;
  backupData: any;
  @Input() filterList: IFilter[] = [];
  @Input() data: any;

  get filters() {
    return this.filterList.filter((filter) => (this.activeFilters?.includes(filter.id)));
  }

  constructor() {
    super();
  }

  ngOnInit() {
    this.availableFilters = this.filterList.map((filter: IFilter) => ({
      id: filter.id,
      name: filter.name,
      display_name: filter.display_name,
      filter_field: filter.filter_field,
    }));

    this.data.subscribe((values: any) => {
      this.preFilteredData = values?.results;
      if (!this.backupData) this.backupData = values;
    });
  }

  clear(filter, event: any) {
    this.filterForm.get(filter).setValue(undefined);
    this.data.next(this.backupData);
  }

  removeFilter(filter, event) {
    this.toggleFilters(filter);
    this.applyFilters();
    event.preventDefault();
  }

  applyFilters() {
    const filters = this.filterForm.value;
    Object.keys(filters).forEach((f) => {
      if (filters[f] === '' || filters[f] === undefined) {
        delete filters[f];
      }
    });
    const data = this.backupData?.results?.filter(function (item) {
      for (let key in filters) {
        if (item[key] === undefined || item[key] !== filters[key]) {
          return false;
        }
      }

      return true;
    });

    this.data.next({...this.backupData, count: data.length, results: data});
  }

  toggleFilters(filter) {
    if (this.activeFilters.includes(filter.id)) {
      this.activeFilters = this.activeFilters.filter((f) => f !== filter.id);
      this.filterForm.removeControl(filter.filter_field);
    } else {
      this.activeFilters.push(filter.id);
      this.filterForm.addControl(filter.filter_field, new FormControl(''))
    }
  }
}
