import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FalseAsEmptyArrayPipe } from './false-as-empty-array.pipe';



@NgModule({
  declarations: [
    FalseAsEmptyArrayPipe
  ],
  exports: [
    FalseAsEmptyArrayPipe
  ],
  imports: [
    CommonModule
  ]
})
export class FalseAsEmptyArrayModule { }
