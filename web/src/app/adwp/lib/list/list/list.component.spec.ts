

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ListComponent } from './list.component';
import { ListConfigService } from "@app/adwp/lib/list/list-config.service";
import { config } from "rxjs";

describe('ListComponent', () => {
  let component: ListComponent<any>;
  let fixture: ComponentFixture<ListComponent<any>>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ListComponent ],
      providers: [
        {
          provide: ListConfigService,
          useValue: config,
        }
      ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
