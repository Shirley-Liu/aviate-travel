/* The original search engine runs in a worker, with no server required. */
let engine;
async function initialize() {
  importScripts('https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.js');
  const py = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v0.28.3/full/'});
  py.FS.mkdirTree('/aviation/data');
  const names = ['search.py','data/SB-airlines.txt','data/SB-airports.txt','data/SB-routes.txt'];
  const contents = await Promise.all(names.map(async name => {
    const response = await fetch(new URL(name.replace(/^data\//, ""), self.location.href));
    if (!response.ok) throw new Error('Unable to load search data: ' + name);
    return new Uint8Array(await response.arrayBuffer());
  }));
  names.forEach((name,i) => py.FS.writeFile('/aviation/' + name, contents[i]));
  await py.runPythonAsync(py.FS.readFile('/aviation/search.py', {encoding:'utf8'}));
  return py;
}
self.onmessage = async ({data:{id,query}}) => {
  try {
    if (!engine) engine = initialize().catch(error => {engine = null; throw error;});
    const py = await engine;
    const search = py.globals.get('search_json');
    let result;
    try { result = search(JSON.stringify(query)); } finally { search.destroy(); }
    self.postMessage({id, result:JSON.parse(result)});
  } catch (error) {
    self.postMessage({id, error:'Search could not load. Check your internet connection and try again. ' + error.message});
  }
};

