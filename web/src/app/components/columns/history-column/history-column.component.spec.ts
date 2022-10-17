import { ComponentFixture, TestBed } from '@angular/core/testing';

import { HistoryColumnComponent } from './history-column.component';

describe('HistoryColumnComponent', () => {
  let component: HistoryColumnComponent;
  let fixture: ComponentFixture<HistoryColumnComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ HistoryColumnComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(HistoryColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
