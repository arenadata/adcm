// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnChanges,
  OnInit,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { AbstractControl, FormControl } from '@angular/forms';
import { fromEvent, merge } from 'rxjs';
import { debounceTime, filter, pluck, tap } from 'rxjs/operators';

import { FieldService } from './../../configuration/field.service';
import { FieldDirective } from '../field.directive';

@Component({
  selector: 'app-fields-password',
  templateUrl: './password.component.html',
  styleUrls: ['./password.component.scss'],
})
export class PasswordComponent extends FieldDirective implements OnInit, AfterViewInit, OnChanges {
  dummy = '********';
  isHideDummy = false;
  value: string;
  constructor(private service: FieldService, private cd: ChangeDetectorRef) {
    super();
  }

  @ViewChild('input', { read: ElementRef }) input: ElementRef;
  @ViewChild('conf', { read: ElementRef }) conf: ElementRef;

  ngOnChanges(changes: SimpleChanges) {
    if (!changes.field.firstChange) {
      this.initConfirm();
    }
  }

  ngOnInit() {
    this.initConfirm();
    super.ngOnInit();

    if (!this.control.value) this.dummy = '';
    this.value = this.control.value;
  }

  initConfirm(): void {
    if (!this.field.ui_options?.no_confirm) {
      this.form.addControl(
        `confirm_${this.field.name}`,
        new FormControl(
          this.field.value,
          this.field.activatable ? [] : this.service.setValidator(this.field, this.control)
        )
      );
    }

    if (this.field.required && !this.field.value) {
      this.hideDummy(false);
    }

    const confirm = this.ConfirmPasswordField;
    if (confirm) confirm.markAllAsTouched();
  }

  ngAfterViewInit(): void {
    const a = fromEvent(this.input.nativeElement, 'blur');
    const b = fromEvent(this.conf.nativeElement, 'blur');
    const c = fromEvent(this.input.nativeElement, 'focus');
    const d = fromEvent(this.conf.nativeElement, 'focus');

    merge(a, b, c, d)
      .pipe(
        debounceTime(100),
        pluck('type'),
        tap((res: 'focus' | 'blur') => {
          if (res === 'blur' && (this.isValidField() || this.isEmpty())) {
            if ((this.isValidField() && this.isEmpty()) || this.isEmpty()) {
              this.control.setValue(this.value);
              this.ConfirmPasswordField.setValue(this.value);
            }

            this.isHideDummy = false;
            this.cd.detectChanges();
          }
        })
      )
      .subscribe();
  }

  isValidField(): boolean {
    return this.control.valid && this.ConfirmPasswordField.valid;
  }

  isEmpty(): boolean {
    return this.control.value === '' && this.ConfirmPasswordField.value === '' && this.value !== '';
  }

  hideDummy(isConfirmField: boolean): void {
    if (this.field.read_only) return null;
    this.isHideDummy = true;
    this.cd.detectChanges();

    if (isConfirmField) {
      this.conf.nativeElement.focus();
    } else {
      this.input.nativeElement.focus();
    }

    this.control.setValue('');
    this.ConfirmPasswordField.setValue('');
  }

  get ConfirmPasswordField(): AbstractControl {
    return this.form.controls['confirm_' + this.field.name];
  }

  inputNewPassword(value: string): void {
    this.control.setValue(value);
    console.log(this.control.value);
    this.confirmPasswordFieldUpdate();
  }

  inputNewConfirmPassword(value: string): void {
    this.ConfirmPasswordField.setValue(value);
  }

  hasErrorConfirm(name: string) {
    const c = this.ConfirmPasswordField;
    return this.getConfirmPasswordFieldErrors(name) && (c.touched || c.dirty);
  }

  confirmPasswordFieldUpdate() {
    this.dummy = this.control.value;
    const confirm = this.ConfirmPasswordField;
    return confirm ? confirm.updateValueAndValidity() : '';
  }

  getConfirmPasswordFieldErrors(error: string) {
    const confirm = this.ConfirmPasswordField;
    if (confirm && confirm.errors) {
      return confirm.errors[error];
    }
    return null;
  }
}
