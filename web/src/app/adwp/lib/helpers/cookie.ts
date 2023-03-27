export class Cookie {

  // returns the cookie with the given name,
  // or undefined if not found
  // https://javascript.info/cookie#getcookie-name
  static get(name: string): string | undefined {
    const matches = document.cookie.match(new RegExp(
      '(?:^|; )' + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)'
    ));
    return matches ? decodeURIComponent(matches[1]) : undefined;
  }

}
