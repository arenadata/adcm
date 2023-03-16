import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '@env/environment';

export interface Stats {
  failed: number;
  success: number;
  running: number;
  aborted: number;
}

@Injectable({
  providedIn: 'root'
})
export class StatsService {

  constructor(
    private http: HttpClient,
  ) { }

  tasks(lastTaskId?: number): Observable<Stats> {
    return this.http.get<Stats>(`${environment.apiRoot}/stats/task/${lastTaskId ?? 0}/`);
  }

}
