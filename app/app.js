const { createServer } = require('node:http');

const hostname = '0.0.0.0';
const port = Number(process.env.PORT) || 8000;

// Config via environment variables (version is kept "in the back")
const APP_MESSAGE = process.env.APP_MESSAGE || 'Hello DevOps Node!';
const APP_VERSION = process.env.APP_VERSION || 'v1';

const server = createServer((req, res) => {
  res.statusCode = 200;
  res.setHeader('Content-Type', 'text/plain; charset=utf-8');

  if (req.url === '/health') {
    res.end('OK');
    return;
  }

  if (req.url === '/version') {
    res.end(APP_VERSION);
    return;
  }

  // Default route: message only (version not shown here)
  res.end(APP_MESSAGE);
});

server.listen(port, hostname, () => {
  console.log(`Server running at http://${hostname}:${port}/`);
});
