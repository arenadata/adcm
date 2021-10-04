import { Directive, Input, TemplateRef } from '@angular/core';
import { IFieldOptions } from '@app/shared/configuration/types';

@Directive({
  selector: '[configField]'
})
export class ConfigFieldMarker {

  @Input()
  get configField(): IFieldOptions {
    return this._options;
  }

  set configField(value: IFieldOptions) {
    this._options = value;
  }

  _options: IFieldOptions = null;


  constructor(public template: TemplateRef<any>) {
  }

}
