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
/**
 * INSTRUCTIONS
 * For the filter to work correctly, you need to create a filter rules with IFilter stucture in filter parent component
 * "copy" of the BehaviourSubject with data for the table and pass it to the table. You must pass both the original
 * and the "copy" to the filter component
 */
import { Component, Input, OnDestroy, OnInit } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { BaseDirective } from "../../../directives";
import { BehaviorSubject } from "rxjs";

export interface IFilter {
  id: number,
  name: string,
  display_name: string,
  filter_field: string,
  filter_type: FilterType,
  options?: IFilterOption[],
  active?: boolean,
}

export interface IFilterOption {
  id: number,
  name: string,
  display_name: string,
  value: any,
}

type FilterType = 'list' | 'input' | 'datetimepicker';

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
              <ng-container [ngSwitch]="filter.filter_type">
                <mat-select *ngSwitchCase="'list'" placeholder="{{ filter.display_name }}" formControlName="{{ filter.filter_field }}"
                            (selectionChange)="applyFilters()">
                  <mat-option *ngFor="let p of filter.options" [value]="p.value">{{ p.display_name }}</mat-option>
                </mat-select>
                <input *ngSwitchCase="'input'" matInput placeholder="{{ filter.display_name }}" formControlName="{{ filter.filter_field }}"
                            (change)="applyFilters()">
              </ng-container>
              <button mat-button matSuffix mat-icon-button aria-label="Clear"
                      *ngIf="clearButtonVisible(filter.filter_field)"
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
  filtersByType = {};
  backupData: any;
  freezeBackupData: boolean = false;
  externalChanges: boolean = false;
  @Input() filterList: IFilter[] = [];
  @Input() externalData: BehaviorSubject<any>;
  @Input() innerData: BehaviorSubject<any>;

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
      filter_type: filter.filter_type
    }));

    this.availableFilters.forEach((i: IFilter) => {
      this.filtersByType[i.filter_field] = i.filter_type;
    })

    this.externalData.subscribe((values: any) => {
      this.externalChanges = true;
      this.freezeBackupData = false;

      if (this.externalChanges && values) {
        this.innerData.next(values);

        this.innerData.subscribe((values: any) => {
          if (!this.backupData || !this.freezeBackupData) {
            this.backupData = values;
            this.freezeBackupData = false;
          }

          if (this.externalChanges) {
            this.externalChanges = false;
            this.applyFilters();
          }
        })
      }
    });
  }

  clear(filter, event: any) {
    this.filterForm.get(filter).setValue(undefined);
    this.innerData.next(this.backupData);
    event.preventDefault();
    event.stopPropagation();
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

    let data = this.backupData?.results?.filter((item) => {
      for (let key in filters) {
        if (this.filtersByType[key] === 'list') {
          if (item[key] === undefined || item[key] !== filters[key]) {
            return false;
          }
        }
      }

      return true;
    });

    if (this.filters.some((f) => f.filter_type === 'input')) {
      data = data.filter((item) => {
        for (let key in filters) {
          if (this.filtersByType[key] === 'input') {
            if (item[key] !== undefined && item[key] !== null && item[key].toLowerCase().includes(filters[key].toLowerCase())) {
              return true;
            }
          }
        }
      })
    }

    this.freezeBackupData = true;
    this.innerData.next({...this.backupData, count: data.length, results: data});
  }

  clearButtonVisible(field) {
    const value = this.filterForm?.getRawValue()[field];
    return value || (typeof value === 'boolean' && !value);
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
