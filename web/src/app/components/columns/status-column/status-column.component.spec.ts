import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StatusColumnComponent } from './status-column.component';
import { MatIconModule } from '@angular/material/icon';

describe('StatusColumnComponent', () => {
  let component: StatusColumnComponent<any>;
  let fixture: ComponentFixture<StatusColumnComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        StatusColumnComponent,
      ],
      imports: [
        MatIconModule,
      ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(StatusColumnComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
