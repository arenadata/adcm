import { Directive, TemplateRef } from '@angular/core';

@Directive({
  selector: '[configField]'
})
export class ConfigFieldMarker {
  constructor(public template: TemplateRef<any>) {
  }

}
