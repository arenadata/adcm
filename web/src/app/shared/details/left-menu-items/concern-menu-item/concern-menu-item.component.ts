import { Component, Input } from '@angular/core';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { environment } from '@env/environment';

@Component({
  selector: 'app-concern-menu-item',
  template: `
    <a mat-list-item
       [appForTest]="'tab_' + link"
       [routerLink]="link"
       routerLinkActive="active"
    >
      <span>{{ label }}</span>&nbsp;
      <ng-container *ngIf="concernsPresent">
        <mat-icon color="warn">
          error_outline
        </mat-icon>
      </ng-container>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class ConcernMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> {

  concernsPresent = false;

  @Input() set entity(entity: BaseEntity) {
    this._entity = entity;
    this.getConcernStatus();
  }

  get entity(): BaseEntity {
    return this._entity;
  }

  constructor(private api: ApiService) {
    super();
  }

  private getConcernStatus(): void {
    const params = {
      owner_type: 'cluster',
      owner_id: this.entity.id + '',
      cause: this.data.cause
    };

    this.api.get(`${environment.apiRoot}/concern`, params)
      .pipe(this.takeUntil()).subscribe((concerns: any[]) => {
      this.concernsPresent = !!concerns?.length;
    });

  }
}
