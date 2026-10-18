from pathlib import Path
import json
import re
import subprocess

root = Path(__file__).resolve().parents[1]
pins = json.loads((root / 'sources.lock.json').read_text())
repos = {'backend': 'ai-it-service-desk', 'web': 'ai-it-service-desk-web'}
for name, repository in repos.items():
    sha = pins[name]
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise SystemExit('Source references must be immutable commit SHAs.')
    target = root / '_sources' / name
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--no-checkout', f'https://github.com/supportflow-ai/{repository}.git', str(target)], check=True)
    status = subprocess.check_output(['git', '-C', str(target), 'status', '--porcelain'], text=True)
    # An initial --no-checkout clone has no worktree yet; later checkouts must be clean.
    if (target / 'README.md').exists() and status.strip():
        raise SystemExit(f'Refusing to overwrite local changes in {target}.')
    subprocess.run(['git', '-C', str(target), 'fetch', 'origin', sha], check=True)
    subprocess.run(['git', '-C', str(target), 'checkout', '--detach', sha], check=True)
