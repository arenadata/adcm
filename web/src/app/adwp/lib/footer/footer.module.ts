import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { FooterComponent } from './footer/footer.component';
import { ConfigService } from '../services/config.service';

@NgModule({
  declarations: [
    FooterComponent,
  ],
  imports: [
    CommonModule,
  ],
  exports: [
    FooterComponent,
  ],
  providers: [
    ConfigService,
  ]
})
export class AdwpFooterModule { }
