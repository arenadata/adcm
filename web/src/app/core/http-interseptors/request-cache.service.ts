// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
import { Injectable } from '@angular/core';
import { HttpRequest, HttpResponse } from '@angular/common/http';

const maxAge = Number.MAX_VALUE; // maximum cache age (ms)

interface RequestCacheEntry {
  url: string;
  response: HttpResponse<any>;
  lastRead: number;
}

export abstract class RequestCache {
  abstract get(req: HttpRequest<any>): HttpResponse<any> | undefined;
  abstract put(req: HttpRequest<any>, response: HttpResponse<any>): void;
}

@Injectable()
export class RequestCacheService implements RequestCache {
  cache = new Map<string, RequestCacheEntry>();

  constructor() {}

  get(req: HttpRequest<any>): HttpResponse<any> | undefined {
    const url = req.urlWithParams;
    const cached = this.cache.get(url);

    if (!cached) return undefined;

    const isExpired = cached.lastRead < Date.now() - maxAge;

    const expired = isExpired ? 'Expired ' : '';
    // this.messanger.add(new Message(`${expired}cached response for "${url}".`));

    return isExpired ? undefined : cached.response;
  }

  put(req: HttpRequest<any>, response: HttpResponse<any>): void {
    const url = req.urlWithParams;
    // this.messanger.add(new Message(`Caching response from "${url}".` ));

    const entry = { url, response, lastRead: Date.now() };
    this.cache.set(url, entry);

    const expired = Date.now() - maxAge;

    this.cache.forEach(c => {
      if (c.lastRead < expired) this.cache.delete(c.url);
    });

    // this.messanger.add(new Message(`Request cache size: ${this.cache.size}.`));
  }
}
