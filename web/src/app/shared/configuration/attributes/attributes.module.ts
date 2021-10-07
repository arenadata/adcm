import { ModuleWithProviders, NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatPseudoCheckboxModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';

import { ATTRIBUTES_OPTIONS, AttributeService, AttributesOptions } from './attribute.service';
import { GroupKeysWrapperComponent } from './attributes/group-keys/group-keys-wrapper.component';
import { ConfigFieldMarker } from './config-field.directive';
import { ConfigFieldAttributeProviderComponent } from './attribute-provider.component';
import { TooltipModule } from '@app/shared/components/tooltip/tooltip.module';

@NgModule({
  declarations: [
    GroupKeysWrapperComponent,
    ConfigFieldMarker,
    ConfigFieldAttributeProviderComponent,
  ],
  imports: [
    CommonModule,
    MatPseudoCheckboxModule,
    MatCheckboxModule,
    MatTooltipModule,
    TooltipModule,
    ReactiveFormsModule,
  ],
  exports: [
    ConfigFieldAttributeProviderComponent,
    ConfigFieldMarker
  ],
  providers: [AttributeService]
})
export class AttributesModule {
  static forRoot(attributeConfig: AttributesOptions): ModuleWithProviders<AttributesModule> {
    return {
      ngModule: AttributesModule,
      providers: [{ provide: ATTRIBUTES_OPTIONS, useValue: attributeConfig }]
    };
  }
}
