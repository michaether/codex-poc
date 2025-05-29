export function initForm() {
  const form = document.querySelector('form');
  const btn = document.getElementById('generateBtn');
  if (!form) return;
  form.addEventListener('submit', () => {
    if (btn) {
      btn.disabled = true;
    }
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
    }
  });
}

export function initCopyButtons() {
  document.querySelectorAll('.copy-btn').forEach((button) => {
    button.addEventListener('click', function () {
      const textElem = this.parentElement.querySelector('.prompt-text');
      if (textElem) {
        const text = textElem.innerText.trim();
        navigator.clipboard.writeText(text);
      }
    });
  });
}
