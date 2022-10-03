import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NameEditColumnComponent } from './name-edit-column.component';

describe('NameEditColumnComponent', () => {
  let component: NameEditColumnComponent;
  let fixture: ComponentFixture<NameEditColumnComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ NameEditColumnComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NameEditColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
