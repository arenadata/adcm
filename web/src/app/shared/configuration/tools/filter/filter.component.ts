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
import { FormControl } from '@angular/forms';
import { BaseDirective } from "../../../directives";
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

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

      <ng-container *ngIf="filterList.length > 0">
        <ng-container *ngFor="let filter of filters">
          <mat-form-field class="filter-field">
            <mat-select placeholder="{{ filter.display_name }}" [(value)]="selectedValue"
                        (selectionChange)="emitItemChanges($event)">
              <mat-option *ngFor="let p of filter.options" [value]="p.id">{{ p.display_name }}</mat-option>
            </mat-select>
            <button mat-button *ngIf="selectedValue" matSuffix mat-icon-button aria-label="Clear"
                    (click)="clear($event)">
              <mat-icon>close</mat-icon>
            </button>
          </mat-form-field>
        </ng-container>
      </ng-container>
    </div>
  `,
  styleUrls: ['./filter.component.scss'],
})
export class FilterComponent extends BaseDirective implements OnInit, OnDestroy {
  filter = new FormControl();
  availableFilters: any[];
  activeFilters: number[] = [];
  selectedValue: any;
  @Input() filterList: IFilter[] = [];

  get filters() {
    return this.filterList.filter((filter) => (this.activeFilters?.includes(filter.id)));
  }

  constructor() {
    super();
  }

  ngOnInit() {
  this.availableFilters = this.filterList.map((filter: IFilter) => ({id: filter.id, display_name: filter.display_name}));

    this.filter.valueChanges
      .pipe(
        this.takeUntil(),
        debounceTime(300),
        distinctUntilChanged())
      .subscribe((value) => console.log(value));
  }

  clear(event: any) {
    this.selectedValue = undefined;
    event.stopPropagation();
  }

  emitItemChanges(event: any) {
    console.log(event);
  }

  toggleFilters(id) {
    if (this.activeFilters.includes(id)) {
      this.activeFilters = this.activeFilters.filter((f) => f !== id);
    } else {
      this.activeFilters.push(id);
    }
  }
}
