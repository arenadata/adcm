import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TaskObjectsComponent } from './task-objects.component';

describe('TaskObjectsComponent', () => {
  let component: TaskObjectsComponent;
  let fixture: ComponentFixture<TaskObjectsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ TaskObjectsComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TaskObjectsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
