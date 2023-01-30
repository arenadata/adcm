import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatListModule } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterModule } from '@angular/router';

import { CrumbsComponent } from './crumbs/crumbs.component';
import { ToolbarComponent } from './toolbar.component';

@NgModule({
  declarations: [ToolbarComponent, CrumbsComponent],
  imports: [
    CommonModule,
    RouterModule,
    MatToolbarModule,
    MatListModule,
    MatIconModule,
    MatTooltipModule,
    MatButtonModule,
  ],
  exports: [ToolbarComponent, CrumbsComponent],
})
export class AdwpToolbarModule {}
