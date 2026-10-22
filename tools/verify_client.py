"""Run focused checks with one JSON summary; retain full output in local logs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from tools.game_config import ROOT


def check_commands(area):
    python = sys.executable
    if area == 'shared':
        return [('shared', [python,'-m','unittest','discover','-s','tests','-p','test_client_tooling.py'])]
    if area == 'cpu':
        return [('cpu', [python,'-m','unittest','discover','-s','tests','-p','test_cpu_strategy.py']),
                ('resolution', [python,'-m','unittest','discover','-s','tests','-p','test_resolution_flow.py'])]
    if area == 'web':
        return [('web', ['bun','test','tests/web_player.test.js','tests/admin_game.test.js'])]
    if area == 'compile':
        return [('compile', [python,'-m','tools.smoke_shared_client','--compile-only'])]
    if area == 'native':
        return [('native', [python,'-m','tools.smoke_shared_client'])]
    return [('python', [python,'-m','unittest','discover','-s','tests']), *check_commands('web')]


def run_checks(commands, output, timeout=1200):
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for name, command in commands:
        log = output/(name+'.log')
        started = time.monotonic()
        try:
            with log.open('w') as stream:
                process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
            code = process.returncode
            status = 'passed' if code == 0 else 'blocked' if code == 77 else 'failed'
            # Compilation is recorded separately from executed runtime checks.
            if name == 'compile' and code == 0:
                status = 'compiled'
            result = {'check':name,'status':status,'seconds':round(time.monotonic()-started,2),'log':str(log)}
            if code != 0:
                text = log.read_text()
                result['detail'] = text[-600:]
                try:
                    child = json.loads(text.strip().splitlines()[-1])
                    reasons = list(dict.fromkeys(item['reason'] for item in child.get('results',[]) if item.get('reason')))
                    if reasons:
                        result['detail'] = '; '.join(reasons)[:600]
                        result['evidence'] = child.get('report')
                except (ValueError, IndexError, TypeError, AttributeError):
                    pass
        except (OSError, subprocess.TimeoutExpired) as error:
            result = {'check':name,'status':'failed','detail':str(error),'log':str(log)}
        results.append(result)
    statuses = {item['status'] for item in results}
    status = 'failed' if 'failed' in statuses else 'blocked' if 'blocked' in statuses else 'compiled' if statuses == {'compiled'} else 'passed'
    report = {'status':status,'checks':results,'report':str(output/'report.json')}
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--area', choices=('shared','cpu','web','all','compile','native'), default='shared')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = run_checks(check_commands(args.area), args.output or ROOT/'.local/verification'/args.area)
    print(json.dumps(report))
    return 1 if report['status'] == 'failed' else 77 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
