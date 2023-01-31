import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AdwpControlsComponent } from './controls.component';

describe('ControlsComponent', () => {
  let component: AdwpControlsComponent;
  let fixture: ComponentFixture<AdwpControlsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AdwpControlsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AdwpControlsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
