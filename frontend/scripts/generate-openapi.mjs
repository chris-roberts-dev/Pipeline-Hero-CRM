import { spawn } from 'node:child_process';

const schemaUrl = process.env.OPENAPI_SCHEMA_URL ?? 'http://localhost:8000/api/internal/schema/';
const output = 'src/lib/api/generated/schema.d.ts';

const child = spawn(
  process.platform === 'win32' ? 'npx.cmd' : 'npx',
  ['openapi-typescript', schemaUrl, '--output', output],
  { stdio: 'inherit' },
);

child.on('exit', (code) => {
  process.exit(code ?? 1);
});
