import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LogMenuItemComponent } from './log-menu-item.component';

describe('LogMenuItemComponent', () => {
  let component: LogMenuItemComponent;
  let fixture: ComponentFixture<LogMenuItemComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ LogMenuItemComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(LogMenuItemComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
