import { IFieldOptions } from './../models/field-options';
import { Directive, Input, OnInit } from '@angular/core';
import { AbstractControl, FormGroup } from '@angular/forms';

@Directive({
  selector: '[adwpField]'
})
export class FieldDirective implements OnInit {

  @Input() form: FormGroup;
  @Input() field: IFieldOptions;

  ngOnInit(): void {
    this.control.markAllAsTouched();
  }

  get control(): AbstractControl {
    return this.form.controls[this.field.name];
  }

  get isValid(): boolean {
    if (this.field.read_only) { return true; }
    const control = this.control;
    return control.valid && (control.dirty || control.touched);
  }

  hasError(name: string): boolean {
    return this.control.hasError(name);
  }

}
