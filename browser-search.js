/* API-compatible bridge for static hosting under any repository path. */
(() => {
  const scriptURL = document.currentScript.src;
  let worker, sequence = 0;
  const pending = new Map();
  function getWorker() {
    if (worker) return worker;
    worker = new Worker(new URL('search-worker.js', scriptURL));
    worker.onmessage = ({data}) => {
      const request = pending.get(data.id);
      if (!request) return;
      pending.delete(data.id);
      request.cleanup();
      if (data.error) request.reject(new Error(data.error));
      else request.resolve({ok:true, status:200, json:async () => data.result});
    };
    worker.onerror = () => {
      for (const request of pending.values()) {
        request.cleanup();
        request.reject(new Error('Search engine could not start. Reload the page to try again.'));
      }
      pending.clear(); worker.terminate(); worker = null;
    };
    return worker;
  }
  window.aviationFetch = (url, options = {}) => new Promise((resolve,reject) => {
    const signal = options.signal;
    if (signal?.aborted) {reject(new DOMException('Aborted','AbortError')); return;}
    const id = ++sequence;
    const abort = () => {pending.delete(id); reject(new DOMException('Aborted','AbortError'));};
    const cleanup = () => signal?.removeEventListener('abort',abort);
    try {
      const target = getWorker();
      pending.set(id,{resolve,reject,cleanup});
      signal?.addEventListener('abort',abort,{once:true});
      target.postMessage({id,query:Object.fromEntries(new URL(url,location.href).searchParams)});
    } catch(error) {pending.delete(id); cleanup(); reject(error);}
  });
})();
