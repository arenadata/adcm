import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ColorTextColumnComponent } from './color-text-column.component';

describe('ColorTextColumnComponent', () => {
  let component: ColorTextColumnComponent;
  let fixture: ComponentFixture<ColorTextColumnComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ColorTextColumnComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ColorTextColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
