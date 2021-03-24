import { ComponentFixture, TestBed } from '@angular/core/testing';

import { IssuesComponent } from './issues.component';
import { KeysPipe } from '@app/pipes/keys.pipe';

describe('IssuesComponent', () => {
  let component: IssuesComponent;
  let fixture: ComponentFixture<IssuesComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        IssuesComponent,
        KeysPipe,
      ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(IssuesComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
