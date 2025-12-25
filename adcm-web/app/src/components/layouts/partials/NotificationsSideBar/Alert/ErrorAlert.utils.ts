export const KNOWN_HTML_TAGS = ['a', 'b', 'i', 'u', 'strong', 'em', 'span', 'div', 'p', 'br', 'ul', 'ol', 'li'];

export const escapeNonHtmlTags = (text: string): string => {
  return text.replace(/<(\/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>/g, (match, _closingSlash, tagName) => {
    const lowerTagName = tagName.toLowerCase();
    if (KNOWN_HTML_TAGS.includes(lowerTagName)) {
      return match;
    }
    return match.replace('<', '&lt;').replace('>', '&gt;');
  });
};
