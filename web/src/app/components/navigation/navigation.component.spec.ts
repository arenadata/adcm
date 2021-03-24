import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';

import { NavigationComponent } from './navigation.component';
import { NavItemPipe } from '@app/pipes/nav-item.pipe';

describe('NavigationComponent', () => {
  let component: NavigationComponent;
  let fixture: ComponentFixture<NavigationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        NavigationComponent,
        NavItemPipe,
      ],
      imports: [
        MatListModule,
        MatIconModule,
      ],
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NavigationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
