import { realpath, stat } from 'node:fs/promises';
import { dirname, isAbsolute, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({
  options: {
    host: { type: 'string', default: process.env.HOST || '127.0.0.1' },
    port: { type: 'string', default: process.env.PORT || '9900' },
    directory: { type: 'string' },
  },
});
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const directory = resolve(values.directory || resolve(root, '.local/website/dist'));
const port = Number(values.port);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('Port must be an integer between 1 and 65535.');
}
if (!(await Bun.file(resolve(directory, 'index.html')).exists())) {
  throw new Error(`Website build missing at ${directory}. Run bun run build:website first.`);
}
const publicRoot = await realpath(directory);
const inside = (path) => {
  const name = relative(publicRoot, path);
  return name !== '..' && !name.startsWith(`..${sep}`) && !isAbsolute(name);
};

const server = Bun.serve({
  hostname: values.host,
  port,
  async fetch(request) {
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      return new Response('Method not allowed', { status: 405, headers: { Allow: 'GET, HEAD' } });
    }
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(request.url).pathname);
    } catch {
      return new Response('Bad request', { status: 400 });
    }
    try {
      let filename = resolve(publicRoot, `.${pathname}`);
      if (!inside(filename)) return new Response('Forbidden', { status: 403 });
      if ((await stat(filename)).isDirectory()) filename = resolve(filename, 'index.html');
      filename = await realpath(filename);
      if (!inside(filename)) return new Response('Forbidden', { status: 403 });
      const file = Bun.file(filename);
      if (!(await stat(filename)).isFile()) return new Response('Not found', { status: 404 });
      return new Response(request.method === 'HEAD' ? null : file, {
        headers: {
          'Content-Type': file.type || 'application/octet-stream',
          'Content-Length': String(file.size),
          'Cache-Control': 'no-cache',
        },
      });
    } catch (error) {
      if (['ENOENT', 'ENOTDIR', 'EACCES'].includes(error.code)) {
        return new Response('Not found', { status: 404 });
      }
      console.error(error);
      return new Response('Internal server error', { status: 500 });
    }
  },
});
console.log(`Serving ${directory}\n${server.url}`);
