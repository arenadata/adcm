import {
  Component,
  ChangeDetectionStrategy,
  ViewEncapsulation,
  ChangeDetectorRef,
  Inject,
  Optional,
  Input,
  HostBinding,
} from '@angular/core';
import {
  MatPaginatorDefaultOptions,
  MatPaginator,
  MatPaginatorIntl,
  MAT_PAGINATOR_DEFAULT_OPTIONS,
} from '@angular/material/paginator';

@Component({
  selector: 'adwp-paginator',
  exportAs: 'adwpPaginator',
  templateUrl: './paginator.component.html',
  styleUrls: ['./paginator.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class PaginatorComponent extends MatPaginator {

  @Input() disabled: boolean;
  @HostBinding('class') klass = 'mat-paginator';

  constructor(intl: MatPaginatorIntl,
              changeDetectorRef: ChangeDetectorRef,
              @Optional() @Inject(MAT_PAGINATOR_DEFAULT_OPTIONS) defaults?: MatPaginatorDefaultOptions) {
    super(intl, changeDetectorRef, defaults);
  }

  goto(page: number): void {
    const previousPageIndex = this.pageIndex;
    this.pageIndex = page - 1;
    this.page.emit({
      previousPageIndex,
      pageIndex: this.pageIndex,
      pageSize: this.pageSize,
      length: this.length,
    });
  }

}
