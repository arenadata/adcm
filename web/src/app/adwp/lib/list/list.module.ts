import { CommonModule } from '@angular/common';
import { ModuleWithProviders, NgModule } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatSortModule } from '@angular/material/sort';
import { MatTableModule } from '@angular/material/table';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { RouterModule } from '@angular/router';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { FormsModule } from '@angular/forms';

import { HoverDirective } from './hover.directive';
import { ListComponent } from './list/list.component';
import { TimePipe } from './pipes/time.pipe';
import { AsStringPipe } from './pipes/as-string.pipe';
import { ComponentCellComponent } from './cell/component-cell.component';
import { ListConfig } from './list-config';
import { ListConfigService } from './list-config.service';
import { ListValuePipe } from './pipes/list-value.pipe';
import { CalcDynamicCellPipe } from './pipes/calc-dynamic-cell.pipe';
import { TableComponent } from './table/table.component';
import { PaginatorComponent } from './paginator/paginator.component';
import { PagesPipe } from './pipes/pages.pipe';
import { LinkCellComponent } from './cell/link-cell.component';
import { ComponentRowComponent } from './row/component-row.component';
import { CalcLinkCellPipe } from './pipes/calc-link-cell.pipe';
import { IsAllCheckedPipe } from './pipes/is-all-checked.pipe';
import { ListCheckboxDisabledPipe } from './pipes/list-checkbox-disabled.pipe';
import { IsIndeterminateCheckedPipe } from './pipes/is-indeterminate-checked.pipe';
import { IsMainCheckboxDisabledPipe } from './pipes/is-main-checkbox-disabled.pipe';

const Material = [
  MatTableModule,
  MatPaginatorModule,
  MatSortModule,
  MatIconModule,
  MatButtonModule,
  MatTooltipModule,
  MatFormFieldModule,
  MatSelectModule,
  MatCheckboxModule,
];

@NgModule({
  declarations: [
    ListComponent,
    HoverDirective,
    TimePipe,
    ListValuePipe,
    ListCheckboxDisabledPipe,
    IsIndeterminateCheckedPipe,
    IsMainCheckboxDisabledPipe,
    AsStringPipe,
    ComponentCellComponent,
    ComponentRowComponent,
    CalcDynamicCellPipe,
    TableComponent,
    PaginatorComponent,
    PagesPipe,
    LinkCellComponent,
    CalcLinkCellPipe,
    IsAllCheckedPipe,
  ],
  imports: [CommonModule, RouterModule, FormsModule, ...Material],
  exports: [ListComponent, TableComponent, TimePipe, LinkCellComponent],
})
export class AdwpListModule {

  public static forRoot(config: ListConfig): ModuleWithProviders<AdwpListModule> {
    return {
      ngModule: AdwpListModule,
      providers: [
        {
          provide: ListConfigService,
          useValue: config,
        }
      ]
    };
  }

}
