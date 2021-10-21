import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LabelMenuItemComponent } from './label-menu-item.component';

describe('LabelMenuItemComponent', () => {
  let component: LabelMenuItemComponent;
  let fixture: ComponentFixture<LabelMenuItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LabelMenuItemComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(LabelMenuItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
