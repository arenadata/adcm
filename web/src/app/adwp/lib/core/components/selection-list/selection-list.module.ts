import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdwpSelectionListComponent } from './selection-list.component';
import { MatPseudoCheckboxModule } from '@angular/material/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatListModule } from '@angular/material/list';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { AdwpMapperPipeModule, AdwpFilterPipeModule } from '../../../cdk';
import { SelectionListActionsComponent } from './selection-list-actions.component';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';


@NgModule({
  declarations: [
    AdwpSelectionListComponent,
    SelectionListActionsComponent
  ],
  imports: [
    CommonModule,
    MatPseudoCheckboxModule,
    MatFormFieldModule,
    MatListModule,
    MatInputModule,
    FormsModule,
    AdwpFilterPipeModule,
    AdwpMapperPipeModule,
    MatIconModule,
    MatButtonModule,
  ],
  exports: [
    AdwpSelectionListComponent
  ]
})
export class AdwpSelectionListModule {
}
