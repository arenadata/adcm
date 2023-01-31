import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AdwpInputComponent } from './input.component';
import {FormControl, FormGroup} from "@angular/forms";

describe('InputComponent', () => {
  let component: AdwpInputComponent;
  let fixture: ComponentFixture<AdwpInputComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AdwpInputComponent ]
    })
    .compileComponents();
  });

  beforeEach( async () => {
    fixture = await TestBed.createComponent(AdwpInputComponent);
    component = fixture.componentInstance;
    component.form = new FormGroup({ name: new FormControl() });
    component.label = 'Group name';
    component.controlName = 'name';
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
