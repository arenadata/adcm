import { Component, Input, OnInit } from '@angular/core';
import { MenuItemAbstractDirective } from '@app/abstract-directives/menu-item.abstract.directive';
import { BaseEntity } from '@app/core/types';
import { ApiService } from '@app/core/api';
import { ConcernService } from '@app/services/concern.service';
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
        <app-concern-list-ref [concerns]="concerns"></app-concern-list-ref>
      </ng-container>
    </a>
  `,
  styles: ['a span { white-space: nowrap; }'],
})
export class ConcernMenuItemComponent extends MenuItemAbstractDirective<BaseEntity> implements OnInit {

  concernsPresent = false;
  concerns = null;

  @Input() set entity(entity: BaseEntity) {
    this._entity = entity;
    this.getConcernStatus();
  }

  get entity(): BaseEntity {
    return this._entity;
  }

  constructor(
    private api: ApiService,
    private concernService: ConcernService
  ) {
    super();
  }

  ngOnInit(): void {
    this.concernService.events({ types: [this.data.type] })
      .pipe(this.takeUntil())
      .subscribe(_ => this.getConcernStatus());
  }

  private getConcernStatus(): void {
    const params = {
      owner_type: this.data.owner_type,
      owner_id: this.entity.id + '',
      cause: this.data.cause
    };

    this.api.get(`${environment.apiRoot}/concern`, params)
      .subscribe((concerns: any[]) => {
        this.concerns = concerns;
        this.concernsPresent = !!concerns?.length
      });
  }
}
