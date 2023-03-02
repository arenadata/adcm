import { Directive, Input } from '@angular/core';
import { BaseDirective } from '@app/adwp';
import { AdcmEntity } from '../models/entity';

@Directive({
  selector: '[appMenuItemAbstract]',
})
export abstract class MenuItemAbstractDirective<EntityType extends AdcmEntity = AdcmEntity> extends BaseDirective {

  protected _entity: EntityType;

  @Input() label: string;
  @Input() link: string;
  @Input() get entity(): EntityType {
      return this._entity;
  }
  set entity(value: EntityType) {
      this._entity = value;
  }
  @Input() data: any;

}
