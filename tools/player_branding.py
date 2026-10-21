"""Generate platform icons from the shared Boufbowl Fan logo using FFmpeg."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
from tools.package_cache import Receipt, digest
from tools.build_parallel import cpu_run, parallel

ANDROID_SIZES = (36, 48, 72, 96, 144, 192, 512)
SIZES = sorted(set(ANDROID_SIZES) | {16, 24, 32, 64, 128, 256})


def build_icons(root, output):
    with Receipt(root, 'icons/'+digest(str(Path(output).absolute()))).lock():
        return _build_icons(root, output)


def _build_icons(root, output):
    root, output = Path(root), Path(output)
    source = root/'assets/branding/logo.png'
    output.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(source.read_bytes()+Path(__file__).read_bytes()).hexdigest()
    receipt = output/'icons.json'
    expected = [f'icon-{size}.png' for size in SIZES]+['icon.ico']
    try:
        previous = json.loads(receipt.read_text())
        if previous['input'] == fingerprint and all(
                hashlib.sha256((output/name).read_bytes()).hexdigest() == previous['files'][name]
                for name in expected):
            return output
    except (OSError, ValueError, KeyError):
        pass
    def render(size):
        filters = (f'scale={size}:{size}:force_original_aspect_ratio=decrease:flags=lanczos,'
                   f'pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color=0x00000000,format=rgba')
        png = output/f'icon-{size}.png'
        cpu_run(['ffmpeg', '-y', '-v', 'error', '-i', str(source), '-vf', filters,
                        '-frames:v', '1', str(png)], check=True)
        if size in (16, 24, 32, 48, 64, 128, 256):
            pixels = cpu_run(['ffmpeg', '-v', 'error', '-i', str(png),
                                             '-vf', 'vflip', '-frames:v', '1', '-f', 'rawvideo',
                                             '-pix_fmt', 'bgra', 'pipe:1'], stdout=subprocess.PIPE, check=True).stdout
            mask_stride = ((size+31)//32)*4
            mask = bytearray(mask_stride*size)
            for y in range(size):
                for x in range(size):
                    if pixels[(y*size+x)*4+3] == 0:
                        mask[y*mask_stride+x//8] |= 1 << (7-x%8)
            header = struct.pack('<IiiHHIIiiII', 40, size, size*2, 1, 32, 0,
                                 len(pixels)+len(mask), 0, 0, 0, 0)
            return size, header+pixels+mask
    bitmaps = sorted(result for result in parallel(render, SIZES) if result is not None)
    offset = 6+16*len(bitmaps)
    entries = []
    for size, bitmap in bitmaps:
        entries.append(struct.pack('<BBBBHHII', size%256, size%256, 0, 0, 1, 32, len(bitmap), offset))
        offset += len(bitmap)
    (output/'icon.ico').write_bytes(struct.pack('<HHH', 0, 1, len(bitmaps))
                                   +b''.join(entries)+b''.join(bitmap for _, bitmap in bitmaps))
    receipt.write_text(json.dumps({'input': fingerprint, 'files': {
        name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in expected}}, indent=2)+'\n')
    return output
