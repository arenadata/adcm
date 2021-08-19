import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ConfigGroupListComponent } from './pages';
import { AdwpListModule } from '@adwp-ui/widgets';
import { AddConfigGroupComponent } from './components';
import { ReactiveFormsModule } from '@angular/forms';
import { MatListModule } from '@angular/material/list';
import { AddingModule } from '@app/shared/add-component/adding.module';
import { FormElementsModule } from '@app/shared/form-elements/form-elements.module';
import { ListService } from '../shared/components/list/list.service';
import { LIST_SERVICE_PROVIDER } from '../shared/components/list/list-service-token';
import { ConfigGroupHostListComponent } from './pages';
import { AddHostToConfigGroupComponent } from './components';


@NgModule({
  declarations: [
    ConfigGroupListComponent,
    AddConfigGroupComponent,
    ConfigGroupHostListComponent,
    AddHostToConfigGroupComponent
  ],
  imports: [
    CommonModule,
    ReactiveFormsModule,
    AdwpListModule,
    MatListModule,
    AddingModule,
    FormElementsModule
  ],
  exports: [
    AddConfigGroupComponent,
  ],
  providers: [
    {
      provide: LIST_SERVICE_PROVIDER,
      useClass: ListService
    }
  ]
})
export class ConfigGroupModule {
}
