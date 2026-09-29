import DOMPurify from 'dompurify';

export const DEFAULT_ALLOWED_TAGS = ['a', 'b', 'i', 'u', 'strong', 'em', 'span', 'div', 'p', 'br', 'ul', 'ol', 'li'];

export const DEFAULT_ALLOWED_ATTR = ['href', 'class', 'target', 'rel'];

export type SanitizeAllowedHtmlOptions = {
  allowedTags?: string[];
  allowedAttrs?: string[];
  /**
   * When true, unknown tags (e.g. `<Host #38>`) are escaped as visible text.
   * When false (default), unknown tags are stripped and their text content is kept.
   */
  preserveUnknownTagsAsText?: boolean;
};

const NON_HTML_TAG_REGEX = /<(\/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>/g;

const ANCHOR_TAG_NAME = 'A';
const TARGET_ATTR_NAME = 'target';
const REL_ATTR_NAME = 'rel';
const TARGET_BLANK = '_blank';
const NOOPENER = 'noopener';
const NOREFERRER = 'noreferrer';
const AFTER_SANITIZE_ATTRIBUTES_HOOK_NAME = 'afterSanitizeAttributes';

export const escapeNonHtmlTags = (text: string, allowedTags: string[]): string => {
  const allowed = new Set(allowedTags.map((t) => t.toLowerCase()));

  return text.replace(NON_HTML_TAG_REGEX, (match, _closingSlash, tagName) => {
    const lowerTagName = String(tagName).toLowerCase();
    if (allowed.has(lowerTagName)) {
      return match;
    }

    return match.replace('<', '&lt;').replace('>', '&gt;');
  });
};

const ensureBlankTargetSafety = (node: Element) => {
  if (node.tagName !== ANCHOR_TAG_NAME) {
    return;
  }

  if (node.getAttribute(TARGET_ATTR_NAME) !== TARGET_BLANK) {
    return;
  }

  const relTokens = new Set((node.getAttribute(REL_ATTR_NAME) ?? '').split(/\s+/).filter(Boolean));
  relTokens.add(NOOPENER);
  relTokens.add(NOREFERRER);
  node.setAttribute(REL_ATTR_NAME, Array.from(relTokens).join(' '));
};

export const sanitizeAllowedHtml = (text: string, options: SanitizeAllowedHtmlOptions = {}): string => {
  const allowedTags = options.allowedTags ?? DEFAULT_ALLOWED_TAGS;
  const allowedAttrs = options.allowedAttrs ?? DEFAULT_ALLOWED_ATTR;
  const preserveUnknownTagsAsText = options.preserveUnknownTagsAsText ?? false;

  const html = preserveUnknownTagsAsText ? escapeNonHtmlTags(text, allowedTags) : text;

  const blankTargetHook = (node: Node) => {
    ensureBlankTargetSafety(node as unknown as Element);
  };

  DOMPurify.addHook(AFTER_SANITIZE_ATTRIBUTES_HOOK_NAME, blankTargetHook);

  try {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: allowedTags,
      ALLOWED_ATTR: allowedAttrs,
      ALLOW_DATA_ATTR: false,
    });
  } finally {
    DOMPurify.removeHook(AFTER_SANITIZE_ATTRIBUTES_HOOK_NAME);
  }
};
