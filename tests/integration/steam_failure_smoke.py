"""Own native Steam initialization failure; never stop/restart clients or send UGC writes."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import tempfile


def verify_failure(runtime_path: Path) -> dict:
    """Run in a separate process with an invalid App ID and an owned temporary appid file."""
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='frontengine-steam-failure-') as directory:
        try:
            os.chdir(directory)
            Path('steam_appid.txt').write_text('4294967295', encoding='ascii')
            os.environ['SteamAppId'] = '4294967295'
            os.environ['SteamGameId'] = '4294967295'
            from frontengine.utils.steam.steam_runtime import SteamRuntime
            runtime = SteamRuntime(runtime_path)
            try:
                assert not runtime.initialize(), 'Invalid App ID must not produce a usable FrontEngine session'
                assert runtime.library is not None and hasattr(runtime.library, 'SteamAPI_InitFlat'), 'Must reach real Steam SDK'
                assert runtime.reason and not runtime.initialized
                assert runtime.poll() == []
                return {'success': True, 'case': 'invalid-app-id-with-existing-client',
                        'native_failure': runtime.reason[:1024], 'session_released': not runtime.initialized,
                        'ugc_writes': 0, 'client_stop_restart': False}
            finally:
                runtime.shutdown()
        finally:
            os.chdir(previous)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        parser.error('This native probe requires Windows x64')
    report = args.report.resolve()
    result = verify_failure(args.runtime.resolve())
    report.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
