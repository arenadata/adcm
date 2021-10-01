import { AfterViewInit, ChangeDetectionStrategy, Component, ContentChild, Input, TemplateRef } from '@angular/core';
import { IFieldOptions } from '@app/shared/configuration/types';
import { ConfigFieldMarker } from '@app/shared/configuration/attribute-provider/config-field.directive';

@Component({
  selector: 'app-config-attribute-provider',
  template: `
    <ng-container *ngIf="field && field.template">
      <ng-template *ngTemplateOutlet="template"></ng-template>
    </ng-container>
  `,
  styles: [
    ':host {display: flex; width: 100%}'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AttributeProviderComponent implements AfterViewInit {
  template: TemplateRef<any>;

  @Input()
  options: IFieldOptions;

  @ContentChild(ConfigFieldMarker) field: ConfigFieldMarker;

  constructor() { }

  ngAfterViewInit(): void {
    console.log(this.options.attributes);
    // console.log('AfterContentInit: ', this.field);
  }

}
