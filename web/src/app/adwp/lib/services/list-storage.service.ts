import { Injectable } from '@angular/core';
import { Paging } from '../list/list/list.component';
import { Sort } from '@angular/material/sort';

@Injectable({
  providedIn: 'root'
})
export class ListStorageService {

  storage: Storage = localStorage;

  protected getItem(key: string): string {
    return this.storage.getItem(key);
  }

  protected setItem(key, value: string): void {
    this.storage.setItem(key, value);
  }

  setPaging(key: string, paging: Paging): void {
    const item = JSON.parse(this.getItem(key) || '{}');
    item.paging = paging;
    this.setItem(key, JSON.stringify(item));
  }

  setSort(key: string, sort: Sort): void {
    const item = JSON.parse(this.getItem(key) || '{}');
    item.sort = sort;
    this.setItem(key, JSON.stringify(item));
  }

  getPaging(key: string): Paging {
    const item = JSON.parse(this.getItem(key));
    if (item && item.paging) {
      return item.paging;
    }

    return null;
  }

  getSort(key: string): Sort {
    const item = JSON.parse(this.getItem(key));
    if (item && item.sort) {
      return item.sort;
    }

    return null;
  }

}
