export async function copy(text: string) {
  try {
    if (navigator.clipboard) {
      await copyTextToClipboard(text);
    } else {
      fallbackCopyTextToClipboard(text);
    }
    return true;
  } catch (e) {
    console.error(e);
  }
  return false;
}

async function copyTextToClipboard(text: string) {
  await navigator.clipboard.writeText(text);
}

function fallbackCopyTextToClipboard(text: string) {
  const textArea = document.createElement('textarea');

  // Avoid scrolling to bottom
  textArea.style.top = '0';
  textArea.style.left = '0';
  textArea.style.position = 'fixed';
  textArea.style.whiteSpace = 'pre';
  textArea.value = text;

  document.body.appendChild(textArea);
  textArea.select();

  try {
    // Obsolete browser API is used to support previous browser versions
    document.execCommand('copy');
  } catch (e) {
    console.error(e);
  }

  document.body.removeChild(textArea);
}
