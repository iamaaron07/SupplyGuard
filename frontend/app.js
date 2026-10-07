const form = document.querySelector('#verify-form');
const input = document.querySelector('#image-input');
const dropzone = document.querySelector('#dropzone');
const preview = document.querySelector('#preview');
const button = document.querySelector('#verify-button');
const error = document.querySelector('#error');
const empty = document.querySelector('#empty-state');
const result = document.querySelector('#result');

input.addEventListener('change', () => {
  const file = input.files[0];
  if (!file) return;
  preview.src = URL.createObjectURL(file);
  dropzone.classList.add('has-image');
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  error.textContent = '';
  button.disabled = true;
  button.querySelector('span').textContent = 'Analyzing package...';
  try {
    const response = await fetch('/api/verify', { method: 'POST', body: new FormData(form) });
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.error || 'Verification failed.');
    empty.classList.add('hidden');
    result.classList.remove('hidden');
    result.classList.toggle('fake', data.prediction === 'FAKE');
    document.querySelector('#prediction').textContent = data.prediction;
    document.querySelector('#confidence').textContent = `${data.confidence_percent}%`;
    document.querySelector('#confidence-bar').style.width = `${data.confidence_percent}%`;
    document.querySelector('#hash').textContent = data.image_sha256;
    document.querySelector('#ledger').textContent = data.blockchain.recorded
      ? `Recorded · ${data.blockchain.transaction_hash || 'transaction submitted'}`
      : data.blockchain.reason;
  } catch (caught) {
    error.textContent = caught.message || 'Backend unavailable.';
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Verify product';
  }
});