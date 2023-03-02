import { switchMap } from 'rxjs/operators';
import { Directive, OnInit } from '@angular/core';

import { BaseDetailAbstractDirective } from './base-detail.abstract.directive';
import { LeftMenuItem } from '@app/shared/details/left-menu/left-menu.component';
import { AdcmEntity } from '@app/models/entity';
import { EntityService } from '@app/abstract/entity-service';

@Directive({
  selector: '[appDetailAbstract]',
})
export abstract class DetailAbstractDirective<EntityType extends AdcmEntity> extends BaseDetailAbstractDirective implements OnInit {

  entity: EntityType;

  abstract leftMenu: LeftMenuItem[];
  protected abstract subjectService: EntityService<EntityType>;
  abstract entityParam: string;

  entityReceived(entity: EntityType): void {
    this.entity = entity;
  }

  ngOnInit() {
    super.ngOnInit();

    this.updateEntity();
  }

  updateEntity() {
    this.route.params.pipe(
      switchMap((params) => this.subjectService.get(params[this.entityParam])),
      this.takeUntil(),
    ).subscribe((entity) => this.entityReceived(entity));
  }

}
