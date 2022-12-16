import {Component, OnChanges, OnInit, ViewChild} from '@angular/core';
import { BaseMapListDirective } from "@app/shared/form-elements/map.component";
import {FormArray, FormControl, FormGroup, FormGroupDirective, NgForm, Validators} from "@angular/forms";
import { TValue } from "@app/shared/configuration/types";
import {first} from "rxjs/operators";
import {ErrorStateMatcher} from "@angular/material/core";

@Component({
  selector: 'app-fields-secret-map',
  templateUrl: './secret-map.component.html',
  styleUrls: ['../map.component.scss', './secret-map.component.scss']
})
export class SecretMapComponent extends BaseMapListDirective implements OnInit, OnChanges {
  @ViewChild("secretInput") secretInput;

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
        if (a) {
          Object.keys(a).forEach((key) => {
            const value = a[key] === '' ? '' : this.dummy
            this.dummyControl.push(new FormGroup({key: new FormControl(key, Validators.required), value: new FormControl(value)}));
          })
        }
      })
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
    const controlValue = { ...this.control.value, [this.dummyControl.value[index].key]: this.dummyControl.value[index].value };
    delete controlValue[""];

    this.control.setValue( controlValue || this.value, { emitEvent: false });
    this.dummyControl.at(index).setValue({ key: this.dummyControl.value[index].key, value: this.dummyControl.value[index] ? this.dummy : '' });
  }

  onFocus(): void {
    this.secretInput.nativeElement.setSelectionRange(this.dummyLength, this.dummyLength);
  }
}

export class MyErrorStateMatcher implements ErrorStateMatcher {
  isErrorState(control: FormControl | null): boolean {
    return !(control?.value !== '' && control?.value !== null);
  }
}
