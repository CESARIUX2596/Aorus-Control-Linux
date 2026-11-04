"""Read-only laptop telemetry and narrowly allow-listed desktop controls."""
import glob
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading

_SAMPLE_LOCK = threading.Lock()
_CPU_SAMPLE = None
FAN_ROOT = Path('/sys/devices/platform/aorus_laptop')


def _read(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, ValueError):
        return None


def _command(args, timeout=2):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _cpu_usage():
    global _CPU_SAMPLE
    data = _read('/proc/stat')
    if not data:
        return None
    fields = data.splitlines()[0].split()[1:]
    try:
        values = [int(value) for value in fields]
    except ValueError:
        return None
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    with _SAMPLE_LOCK:
        previous = _CPU_SAMPLE
        _CPU_SAMPLE = (total, idle)
    if previous is None or total <= previous[0]:
        return None
    elapsed = total - previous[0]
    return round(100 * (1 - (idle - previous[1]) / elapsed))


def _sensors():
    readings = []
    cpu = []
    gpu = []
    fans = []
    for directory in glob.glob('/sys/class/hwmon/hwmon*'):
        name = _read(Path(directory) / 'name') or 'Sensor'
        for file in glob.glob(directory + '/temp*_input'):
            raw = _read(file)
            if raw is None:
                continue
            try:
                value = round(int(raw) / 1000, 1)
            except ValueError:
                continue
            label = _read(file.removesuffix('_input') + '_label')
            if not label and name == 'aorus_laptop':
                index = Path(file).name[4:-6]
                label = {"1": "CPU", "2": "GPU", "3": "Motherboard"}.get(index)
            label = label or name
            entry = {'name': label, 'celsius': value, 'source': name}
            readings.append(entry)
            if name == 'coretemp':
                cpu.append(value)
            if name.lower() in ('amdgpu', 'nouveau'):
                gpu.append(value)
        for file in glob.glob(directory + '/fan*_input'):
            raw = _read(file)
            if raw and raw.isdigit() and int(raw) > 0:
                index = Path(file).name[3:-6]
                label = _read(Path(directory) / f'fan{index}_label')
                if not label and name == 'aorus_laptop':
                    label = {"1": "CPU fan", "2": "GPU fan"}.get(index, f'Fan {index}')
                label = label or f'{name} fan {index}'
                fans.append({'name': label, 'rpm': int(raw)})
    return readings, max(cpu) if cpu else None, max(gpu) if gpu else None, fans


def _nvidia():
    if not shutil.which('nvidia-smi'):
        return None
    output = _command([
        'nvidia-smi', '--query-gpu=temperature.gpu,utilization.gpu,power.draw,power.limit',
        '--format=csv,noheader,nounits',
    ], timeout=2)
    if not output:
        return None
    fields = [part.strip() for part in output.splitlines()[0].split(',')]
    try:
        number = lambda value: float(value) if value.strip().lower() not in ('n/a', '[n/a]', '[not supported]') else None
        return {'temperature': number(fields[0]), 'utilization': number(fields[1]),
                'power_watts': number(fields[2]), 'power_limit_watts': number(fields[3])}
    except (IndexError, ValueError):
        return None


def _battery():
    for directory in glob.glob('/sys/class/power_supply/BAT*'):
        capacity = _read(Path(directory) / 'capacity')
        if capacity is None:
            continue
        try:
            return {'percent': max(0, min(100, int(capacity))), 'status': _read(Path(directory) / 'status') or 'Unknown'}
        except ValueError:
            pass
    return None


def _charging_limit():
    mode = _read(FAN_ROOT / 'charge_mode')
    limit = _read(FAN_ROOT / 'charge_limit')
    if mode is None or limit is None:
        return {'available': False, 'limit': None}
    try:
        return {'available': True, 'enabled': int(mode) == 1, 'limit': int(limit)}
    except ValueError:
        return {'available': False, 'limit': None}


def _fan_control():
    node = FAN_ROOT / 'fan_mode'
    if not node.exists():
        return {'available': False, 'reason': 'Fan control driver not detected. Install and validate the Gigabyte WMI driver for this laptop to enable it.'}
    try:
        modes = [int(x) for x in (_read(FAN_ROOT / 'fan_mode_choices') or '0 1 2 3 4 5').replace(',', ' ').split()]
        current = int(_read(node))
        custom_speed = _read(FAN_ROOT / 'fan_custom_speed')
        custom_speed = int(custom_speed) if custom_speed is not None else None
    except (TypeError, ValueError):
        return {'available': False, 'reason': 'The detected fan driver does not expose a readable mode.'}
    labels = {0: 'Normal', 1: 'Silent', 2: 'Gaming', 4: 'Auto maximum', 5: 'Fixed speed'}
    return {'available': True, 'current': current, 'custom_speed': custom_speed,
            'speed_available': (FAN_ROOT / 'fan_custom_speed').exists(),
            'modes': [{'value': key, 'name': value} for key, value in labels.items() if key in modes]}


def _power_profiles():
    if not shutil.which('powerprofilesctl'):
        return None
    current = _command(['powerprofilesctl', 'get'])
    available = _command(['powerprofilesctl', 'list']) or ''
    profiles = [name for name in ('power-saver', 'balanced', 'performance') if re.search(rf'(?m)^\s*\*?\s*{re.escape(name)}\s*:', available)]
    return {'current': current, 'profiles': profiles}


def _wireless():
    wifi = _command(['nmcli', '-t', '-f', 'WIFI', 'general']) if shutil.which('nmcli') else None
    bluez = _command(['bluetoothctl', 'show']) if shutil.which('bluetoothctl') else None
    bt_power = re.search(r'(?m)^\s*Powered:\s*(yes|no)', bluez or '')
    bluetooth = _command(['rfkill', 'list', 'bluetooth']) if shutil.which('rfkill') else None
    bt_blocked = (bt_power.group(1) == 'no') if bt_power else (None if not bluetooth else any('Soft blocked: yes' in line for line in bluetooth.splitlines()))
    return {'wifi': wifi.lower() if wifi else None, 'bluetooth_blocked': bt_blocked}


def _audio():
    output = _command(['wpctl', 'get-volume', '@DEFAULT_AUDIO_SINK@']) if shutil.which('wpctl') else None
    if not output:
        return None
    match = re.search(r'Volume:\s*([0-9.]+)', output)
    if not match:
        return None
    return {'percent': round(float(match.group(1)) * 100), 'muted': '[MUTED]' in output}


def snapshot():
    readings, cpu_temp, gpu_temp, fans = _sensors()
    gpu = _nvidia()
    if gpu:
        gpu_temp = gpu['temperature']
    battery = _battery()
    model = _read('/sys/class/dmi/id/product_name') or 'AORUS laptop'
    return {
        'cpu': {'usage': _cpu_usage(), 'temperature': cpu_temp},
        'gpu': {**(gpu or {}), 'temperature': gpu_temp},
        'temperature_sensors': readings[:16],
        'fans': fans,
        'fan_control': _fan_control(),
        'battery': battery,
        'charging_limit': _charging_limit(),
        'model': model,
        'power_profiles': _power_profiles(),
        'wireless': _wireless(),
        'audio': _audio(),
        'features': {
            'wifi': bool(shutil.which('nmcli')),
            'bluetooth': bool(shutil.which('bluetoothctl') or shutil.which('rfkill')),
            'audio': bool(shutil.which('wpctl')),
        },
    }


def _run(args, timeout=4):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[:240]
        raise ValueError(detail or 'The system control command failed.')


def action(name, value, demo=False):
    if demo:
        raise ValueError('System controls are disabled in preview mode.')
    if name == 'power-profile' and value in ('power-saver', 'balanced', 'performance'):
        state = _power_profiles()
        if not state or value not in state['profiles']:
            raise ValueError('That power profile is not available on this system.')
        _run(['powerprofilesctl', 'set', value])
    elif name == 'fan-mode' and value in ('0', '1', '2', '4', '5'):
        state = _fan_control()
        if not state['available'] or not any(str(m['value']) == value for m in state['modes']):
            raise ValueError('Fan control is unavailable. The Gigabyte WMI driver and this mode must be detected first.')
        helper = '/usr/local/sbin/aorus-lighting-boot'
        _run(['sudo', '-n', helper, 'fan-mode', value])
    elif name == 'fan-speed' and value in ('25', '50', '75', '100'):
        state = _fan_control()
        if not state['available'] or not state['speed_available']:
            raise ValueError('Fixed fan speed control is unavailable.')
        _run(['sudo', '-n', '/usr/local/sbin/aorus-lighting-boot', 'fan-speed', value])
    elif name == 'charge-limit' and value in ('default', '60', '80', '100'):
        if not _charging_limit()['available']:
            raise ValueError('Charging-limit control is not exposed by the current laptop driver.')
        _run(['sudo', '-n', '/usr/local/sbin/aorus-lighting-boot', 'charge-limit', value])
    elif name == 'wifi' and value in ('on', 'off') and shutil.which('nmcli'):
        _run(['nmcli', 'radio', 'wifi', value])
    elif name == 'bluetooth' and value in ('on', 'off') and shutil.which('bluetoothctl'):
        _run(['bluetoothctl', 'power', value])
    elif name == 'bluetooth' and value in ('on', 'off') and shutil.which('rfkill'):
        _run(['rfkill', 'unblock' if value == 'on' else 'block', 'bluetooth'])
    elif name == 'volume' and value in ('up', 'down', 'mute') and shutil.which('wpctl'):
        if value == 'mute':
            args = ['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', 'toggle']
        else:
            current = _audio()
            level = current['percent'] if current else 50
            level = max(0, min(100, level + (5 if value == 'up' else -5)))
            args = ['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', f'{level / 100:.2f}']
        _run(args)
    else:
        raise ValueError('That laptop action is not supported here.')
    return {'ok': True, 'system': snapshot()}
