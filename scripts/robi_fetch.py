"""Fetch a small subset of ROBI [S-05] with HTTP range requests (the per-object archives are uncompressed zips of ~4 GB).

Usage: .venv/bin/python -I scripts/robi_fetch.py <drive_file_id> <out_dir> --list
       .venv/bin/python -I scripts/robi_fetch.py <drive_file_id> <out_dir> --views-per-scene 12

Only the D415 data of the chosen views is fetched: RealSense/Depth, RealSense/StereoPattern (left and right, with their
pose JSON) and GT_world2obj.json. Views are every k-th entry of RealSense/list.txt, so the choice does not look at any
outcome. Files are treated as data and only read, never executed. ROBI is CC BY-NC-SA 4.0: it is not redistributed here.
"""

import argparse
import io
import re
import time
import urllib.request
import zipfile
from pathlib import Path

URL = "https://drive.usercontent.google.com/download?id={}&export=download&confirm=t"
UA = {"User-Agent": "robi-subset-fetch/1.0"}


class HttpRangeFile(io.RawIOBase):
    """Read-only seekable file over HTTP range requests, with a small read-ahead buffer."""

    def __init__(self, url, chunk=1 << 20):
        self.url, self.chunk, self.pos = url, chunk, 0
        self.buf, self.buf_start = b"", 0
        self.size = int(self._get(0, 0)[1].split("/")[-1])
        self.requests, self.bytes = 0, 0

    def _get(self, a, b):
        req = urllib.request.Request(self.url, headers={**UA, "Range": f"bytes={a}-{b}"})
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    cr = r.headers.get("Content-Range")
                    if r.status != 206 or cr is None:
                        raise RuntimeError(f"no partial content (status {r.status}): the quota page, stop rather than retry around it")
                    return r.read(), cr
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(5 * (attempt + 1))
        raise RuntimeError("unreachable")

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        end = self.pos + n
        if not (self.buf_start <= self.pos and end <= self.buf_start + len(self.buf)):
            b = max(end, self.pos + self.chunk) - 1
            self.buf, _ = self._get(self.pos, min(b, self.size - 1))
            self.buf_start = self.pos
            self.requests += 1
            self.bytes += len(self.buf)
        out = self.buf[self.pos - self.buf_start:end - self.buf_start]
        self.pos = end
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file_id")
    ap.add_argument("out", type=Path)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--views-per-scene", type=int, default=12)
    args = ap.parse_args()
    f = HttpRangeFile(URL.format(args.file_id))
    z = zipfile.ZipFile(f)
    names = [i.filename for i in z.infolist()]
    scenes = sorted({m.group(1) for n in names if (m := re.match(r"(.+/Scene_\d+)/", n))}, key=lambda s: int(s.rsplit("_", 1)[1]))
    print("size", f.size, "members", len(names), "scenes", len(scenes), flush=True)
    if args.list:
        print("\n".join(n for n in names if "Scene_1/" in n and not re.search(r"view_\d+\.", n)))
        print("\n".join(n for n in names if "Scene_1/RealSense" in n and re.search(r"view_(0|1)\.", n)))
        for s in scenes:
            print(s, "depth", sum(n.startswith(s + "/RealSense/Depth/") and n.endswith(".png") for n in names),
                  "pattern", sum(n.startswith(s + "/RealSense/StereoPattern/") and n.endswith(".bmp") for n in names),
                  "gt_raw", sum(n.startswith(s + "/GT_Depth") and n.endswith(".png") for n in names))
        return
    wanted = []
    for s in scenes:
        have = set(names)
        wanted += [n for n in (f"{s}/GT_world2obj.json", f"{s}/RealSense/list.txt") if n in have]
        views = sorted({int(m.group(1)) for n in names if n.startswith(s + "/RealSense/Depth/") and (m := re.search(r"DEPTH_view_(\d+)\.png$", n))})
        step = max(1, len(views) // args.views_per_scene)
        for v in views[::step][:args.views_per_scene]:
            for rel in (f"Depth/DEPTH_view_{v}.png", f"Depth/DEPTH_view_{v}.json", f"StereoPattern/LEFT_view_{v}.bmp", f"StereoPattern/LEFT_view_{v}.json",
                        f"StereoPattern/RIGHT_view_{v}.bmp", f"StereoPattern/RIGHT_view_{v}.json"):
                n = f"{s}/RealSense/{rel}"
                if n in have:
                    wanted.append(n)
    print("fetching", len(wanted), "files", flush=True)
    t0 = time.time()
    for i, n in enumerate(wanted):
        dst = args.out / n
        info = z.getinfo(n)
        if dst.exists() and dst.stat().st_size == info.file_size:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".part")
        tmp.write_bytes(z.read(info))
        tmp.rename(dst)
        if i % 100 == 0:
            print(i, n, f"{f.bytes / 1e6:.0f} MB in {time.time() - t0:.0f} s", flush=True)
    print("DONE", len(wanted), f"{f.bytes / 1e6:.0f} MB, {f.requests} requests, {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
