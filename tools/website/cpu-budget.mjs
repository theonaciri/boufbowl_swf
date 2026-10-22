import { availableParallelism } from 'node:os';
import { readFileSync } from 'node:fs';
import path from 'node:path';

export function cpuCount() {
  let count = availableParallelism();
  try {
    const group = readFileSync('/proc/self/cgroup', 'utf8').split('\n').find(line => line.startsWith('0::')).slice(3);
    let directory = path.resolve('/sys/fs/cgroup', '.' + group);
    if (!directory.startsWith('/sys/fs/cgroup/')) directory = '/sys/fs/cgroup';
    try { readFileSync(path.join(directory, 'cpu.max')); } catch { directory = '/sys/fs/cgroup'; }
    while (directory.startsWith('/sys/fs/cgroup')) {
      try {
        const [quota, period] = readFileSync(path.join(directory, 'cpu.max'), 'utf8').trim().split(/\s+/);
        if (quota !== 'max') count = Math.min(count, Math.max(1, Math.ceil(Number(quota) / Number(period))));
      } catch {}
      directory = path.dirname(directory);
    }
  } catch {}
  try {
    for (const line of readFileSync('/proc/self/cgroup', 'utf8').trim().split('\n')) {
      const [, controllers, group] = line.split(':');
      if (!controllers.split(',').includes('cpu')) continue;
      for (const mount of ['/sys/fs/cgroup/cpu', '/sys/fs/cgroup/cpu,cpuacct']) {
        let directory = path.resolve(mount, '.' + group);
        if (!directory.startsWith(mount + '/')) directory = mount;
        // Check the mounted controller root even in a cgroup namespace.
        try { readFileSync(path.join(directory, 'cpu.cfs_quota_us')); } catch { directory = mount; }
        while (directory === mount || directory.startsWith(mount + '/')) {
          try {
            const quota = Number(readFileSync(path.join(directory, 'cpu.cfs_quota_us'), 'utf8'));
            const period = Number(readFileSync(path.join(directory, 'cpu.cfs_period_us'), 'utf8'));
            if (quota > 0) count = Math.min(count, Math.max(1, Math.ceil(quota / period)));
          } catch {}
          directory = path.dirname(directory);
        }
      }
    }
  } catch {}
  if (process.env.BOUFBOWL_BUILD_CPUS) count = Math.min(count, Number(process.env.BOUFBOWL_BUILD_CPUS));
  if (!Number.isInteger(count) || count < 1) throw Error('Invalid build CPU budget');
  return count;
}

let running = 0;
const waiters = [];
export async function cpuJob(work) {
  const address = process.env.BOUFBOWL_BUILD_BUDGET;
  if (address) {
    // Media tasks can hold every slot for longer than Bun's five-minute idle
    // timeout. Waiting for a CPU slot is expected; match Python's 24-hour limit.
    const response = await fetch(address + '/acquire?pid=' + process.pid, {
      timeout: false,
      signal: AbortSignal.timeout(86400000),
    });
    if (!response.ok) throw Error('Build CPU budget is unavailable');
    const { token } = await response.json();
    try { return await work(); }
    finally {
      const released = await fetch(address + '/release', { method: 'POST', body: token });
      if (!released.ok) throw Error('Could not release build CPU job');
    }
  }
  if (running >= cpuCount()) await new Promise(resolve => waiters.push(resolve));
  else running++;
  try { return await work(); }
  finally {
    if (waiters.length) waiters.shift()();
    else running--;
  }
}

// Each worker reuses its own Ruffle page; only independent tasks run together.
export async function renderTasks(tasks, createPage, render) {
  let next = 0;
  let failed = false;
  const results = await Promise.allSettled(Array.from({ length: Math.min(cpuCount(), tasks.length) }, async () => {
    let page;
    try {
      while (!failed && next < tasks.length) {
        const task = tasks[next++];
        await cpuJob(async () => {
          if (failed) return;
          if (!page) page = await createPage();
          try { await render(task, page); }
          finally {
            await page.evaluate(() => {
              for (const player of [window.p, window.puppetPlayer]) if (player) player.ruffle().suspend();
            }).catch(() => {});
          }
        });
      }
    } catch (error) { failed = true; throw error; }
    finally { if (page) await page.close(); }
  }));
  const error = results.find(result => result.status === 'rejected');
  if (error) throw error.reason;
}
