import { createServer } from 'http';
import { spawn } from 'child_process';

const PORT = 3031;

process.on('unhandledRejection', (e) => console.error('[med-llm] Unhandled rejection:', e));

function callZAI(userPrompt, systemPrompt) {
  return new Promise((resolve, reject) => {
    const args = ['chat', '-p', userPrompt];
    if (systemPrompt) args.push('--system', systemPrompt);
    const child = spawn('z-ai', args, { stdio: ['pipe', 'pipe', 'pipe'], timeout: 90_000 });
    let stdout = '', stderr = '';
    child.stdout.on('data', (d) => (stdout += d));
    child.stderr.on('data', (d) => (stderr += d));
    child.on('close', (code) => {
      if (code !== 0) return reject(new Error(`z-ai exited ${code}: ${stderr.slice(0, 200)}`));
      try {
        const lines = stdout.split('\n');
        const i = lines.findIndex((l) => l.trim().startsWith('{'));
        if (i < 0) throw new Error('No JSON in output');
        resolve(JSON.parse(lines.slice(i).join('\n')).choices[0].message.content);
      } catch (e) {
        reject(e);
      }
    });
    child.on('error', reject);
  });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on('data', (c) => chunks.push(c));
    req.on('end', () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch (e) {
        reject(e);
      }
    });
    req.on('error', reject);
  });
}

const server = createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.writeHead(204).end();

  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ status: 'ok', provider: 'z-ai-medllm' }));
  }

  if (req.method === 'POST' && req.url === '/complete') {
    try {
      const body = await readBody(req);
      if (!body.user) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ error: '"user" required' }));
      }
      const response = await callZAI(body.user, body.system);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ response }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ error: e.message }));
    }
  }

  res.writeHead(404).end('Not found');
});

server.on('error', (e) => console.error('[med-llm] Server error:', e.message));
server.listen(PORT, () => console.log(`[med-llm] Listening on ${PORT}`));
