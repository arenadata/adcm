import {Component, ElementRef, OnChanges, OnInit, QueryList, ViewChild, ViewChildren} from '@angular/core';
import { BaseMapListDirective } from "@app/shared/form-elements/map.component";
import {FormArray, FormControl, FormGroup, Validators} from "@angular/forms";
import { TValue } from "@app/shared/configuration/types";
import {ErrorStateMatcher} from "@angular/material/core";

@Component({
  selector: 'app-fields-secret-map',
  templateUrl: './secret-map.component.html',
  styleUrls: ['../map.component.scss', './secret-map.component.scss']
})
export class SecretMapComponent extends BaseMapListDirective implements OnInit, OnChanges {
  @ViewChildren("secretInput") secretInput: QueryList<ElementRef>;

  dummy = '********';
  dummyLength = this.dummy.length;
  dummyControl = new FormArray([]);
  value: TValue;
  asList = false;
  matcher = new MyErrorStateMatcher();

  ngOnChanges(): void {
    this.value = this.field?.value;

    this.control.valueChanges
      .pipe(this.takeUntil())
      .subscribe((a) => {
        this.dummyControl.clear();
        if (a === null) {
          this.items.clear();
        } else {
          this.items.controls.forEach((control, i) => {
            const itemsValue = control.value.value === '' || control.value.value === null ? null : this.dummy
            this.dummyControl.push(new FormGroup({
              key: new FormControl(control.value.key, Validators.required),
              value: new FormControl(itemsValue)
            }));
          });
        }
      })

      this.control.statusChanges
        .pipe(this.takeUntil())
        .subscribe((state) => {
          if (state === 'DISABLED') {
            this.dummyControl.controls.forEach((control) => {
              control.disable({ emitEvent: false });
              control.markAsUntouched();
            });
            this.control.markAsUntouched();
          } else {
            this.dummyControl.controls.forEach((control) => {
              control.enable({ emitEvent: false });
              control.markAsTouched();
            });
            this.control.markAsTouched();
          }
      });
  }

  ngOnInit() {
    super.ngOnInit();

    if (this.field?.value) {
      Object.keys(this.field.value)?.forEach((key, i) => {
        this.dummyControl.push(new FormGroup({
            key: new FormControl(key, Validators.required),
            value: new FormControl(this.field.value[key]),
          }
        ));

        this.dummyControl.at(i).patchValue({ key: key, value: this.dummy }, { emitEvent: false });
      })
    }
  }

  onBlur(index): void {
    const controlValue = { 
      key: this.dummyControl.value[index].key, 
      value: this.dummyControl.value[index].value !== this.dummy ? this.dummyControl.value[index].value : this.control.value[this.dummyControl.value[index].key]
    };
    this.items.at(index).setValue(controlValue);
  }

  onFocus(index): void {
    this.secretInput.get(index).nativeElement.value = '';
  }

  validate() {
    const obj = {};
    this.dummyControl.value.forEach((i) => obj[i.key] = i.value);
    this.control.patchValue(obj, { emitEvent: false });
    this.control.updateValueAndValidity({ emitEvent: false })
  }
}

export class MyErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    return !(control?.value !== '' && control?.value !== null);
  }
}
