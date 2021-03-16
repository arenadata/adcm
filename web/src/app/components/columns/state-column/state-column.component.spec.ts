import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StateColumnComponent } from './state-column.component';

describe('StateColumnComponent', () => {
  let component: StateColumnComponent<any>;
  let fixture: ComponentFixture<StateColumnComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ StateColumnComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(StateColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
