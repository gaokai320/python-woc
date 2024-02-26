#!/usr/bin/env python3

# SPDX-License-Identifier: GPL-3.0-or-later
# @authors: Runzhi He <rzhe@pku.edu.cn>
# @date: 2024-01-17

import os
import json
import logging
import argparse
import re
from typing import Dict, Iterable, Tuple, Optional
from functools import cmp_to_key

DEFAULT_PROFILE = os.path.join(os.path.dirname(__file__), 'wocprofile.default.json')
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.INFO)

MAP_REGEX = r"^(\w+)2(\w+)Full(\w+)(?:.(\d+))?.tch$"
_map_pat = re.compile(MAP_REGEX)
def parse_map_fname(fname: str):
    """
    Parse basemap filename into (src, dst, ver, idx)
    >>> parse_map_fname('c2fFullR.3.tch')
    ('c', 'f', 'R', '3')
    >>> parse_map_fname('c2fFullR.tch')
    ('c', 'f', 'R', None)
    """
    m = _map_pat.match(fname)
    if not m or len(m.groups()) != 4:
        return None
    return m.groups()

LARGE_REGEX = r"^(\w+)2(\w+)Full(\w+)(?:.(\d+))?.tch.large.([0-9a-f]+)$"
_large_pat = re.compile(LARGE_REGEX)
def parse_large_fname(fname: str):
    """
    Parse basemap filename into (src, dst, ver, idx, hash)
    >>> parse_large_fname('A2cFullU.15.tch.large.59016a4f')
    ('A', 'c', 'U', '15', '59016a4f')
    """
    m = _large_pat.match(fname)
    if not m or len(m.groups()) != 5:
        return None
    return m.groups()

OBJ_REGEX = r"^([\w\.]+)_(\d+).(idx|bin|tch)$"
_obj_pat = re.compile(OBJ_REGEX)
def parse_obj_fname(fname: str):
    """
    Parse sha1map (sha1o/sha1c/blob) filename into (name, idx, ext)
    >>> parse_obj_fname('commit_0.tch')
    ('commit', '0', 'tch')
    >>> parse_obj_fname('blob_0.idx')
    ('blob', '0', 'idx')
    >>> parse_obj_fname('sha1.blob_0.bin')
    ('sha1.blob', '0', 'bin')
    """
    m = _obj_pat.match(fname)
    if not m or len(m.groups()) != 3:
        return None
    return m.groups()

def compare_woc_version(ver1: str, ver2: str):
    """
    Compare two woc version strings (A < Z < AA)
    >>> compare_woc_version('S', 'T') > 0
    False
    >>> compare_woc_version('AA', 'U') > 0
    True
    """
    if len(ver1) != len(ver2):
        return len(ver1) - len(ver2)
    return ord(ver1[0]) - ord(ver2[0])

def infer_dtype(map_name: str) -> Tuple[str, str]:
    """
    Infer the data types from the map's name (entity -> entity)
    Should be bug-to-bug compatible with:
    https://github.com/ssc-oscar/lookup/blob/7289885/getValues.perl#L34
    >>> infer_dtype('c2f')
    ('h', 'cs')
    >>> infer_dtype('b2tac')
    ('h', 'cs3')
    """
    ent_all = map_name.lower()
    ent_in, ent_out = ent_all.split('2')

    dtype_in, dtype_out = 'h', 'h'

    if ent_in in ('a', 'f', 'p'):
        dtype_in = 's'
    if ent_out in ('a', 'f', 'p'):
        dtype_out = 'cs'
    if ent_in in ('c','b','w','ob','td'):
        dtype_in = 'h'
    if ent_out in ('c','b','cc', 'pc','ob','td'):
        dtype_out = 'h'
    if ent_all == 'b2fa':
        dtype_out = 'sh'
    if ent_out in ('ta',):
        dtype_out = 's'
    if ent_all in ('b2tk', 'td2f'):
        dtype_out = 's'
    if ent_all in ('c2h', 'c2r'):
        dtype_out = 'r'
    if ent_in in ('ps', 'pf', 'pfs'):
        dtype_in = 's'
    if ent_out in ('ps', 'pf', 'pfs'):
        dtype_out = 's'
    if ent_out in ('rhp',):
        dtype_out = 'hhwww'
    if ent_all in ('p2p', 'a2a'):
        dtype_in, dtype_out = 's', 'cs'
    if ent_all in ('b2baddate', 'b2manyp'):
        dtype_in, dtype_out = 's', 'h'
    if ent_all in ('c2fbb', 'obb2cf', 'bb2cf'):
        dtype_in, dtype_out = 'h', 'cs'
    if ent_all in ('c2fbb', 'obb2cf', 'bb2cf'):
        dtype_in, dtype_out = 'h', 'cs'
    if ent_all in ('c2dat',):
        dtype_in, dtype_out = 'h', 's'
    if ent_all in ('b2tac',):
        dtype_in, dtype_out = 'h', 'cs3'

    return dtype_in, dtype_out

def detect_profile(
    paths: Iterable[str],
    version: Optional[str] = None,
    preset_path: str = DEFAULT_PROFILE,
):
    _maps, _objs = {}, {}

    def _handle_map(src, dst, ver, idx, hash):
        if version and ver != version:
            logging.info(f'Found map {f} with version {ver}, expected {version}')
            return

        _map_name = f'{src}2{dst}'
        if idx is None:
            idx = "0"
        prefix_len = int(idx).bit_length() 

        _map = (_maps
            .setdefault(_map_name, {})
            .setdefault(ver, {
                "version": ver,
                "sharding_bits": prefix_len,
                "shards": {},
                "larges": {},
                "dtypes": infer_dtype(_map_name),
            })
        )
        if not hash:
            logging.debug(f'Found map {f} with hash {hash} idx {idx}')
            _map["shards"][int(idx)] = os.path.join(root, f)
        else:
            logging.debug(f'Found large map {f} with hash {hash} idx {idx}')
            _map["larges"][hash] = os.path.join(root, f)
        _map["sharding_bits"] = max(_map["sharding_bits"], prefix_len)


    def _handle_obj(name, idx, ext):
        _map_name = f"{name}.{ext}"
        prefix_len = int(idx).bit_length() if idx else 0
        _obj = (_objs
            .setdefault(_map_name, {
                "sharding_bits": prefix_len,
                "shards": {},
            })
        )
        logging.debug(f'Found obj {f} idx {idx}')
        _obj["shards"][int(idx)] = os.path.join(root, f)
        _obj["sharding_bits"] = max(_obj["sharding_bits"], prefix_len)


    for path in paths:
        # walk the directory for all files
        for root, _, files in os.walk(path):
            # only consider .tch, .idx, .bin files
            files = [f for f in files if '.tch' in f or (not f.startswith('pack') and f.endswith('.idx')) or f.endswith('.bin')]
            for idx, f in enumerate(files):
                if idx % 1000 == 0:
                    _logger.info(f'Processing {f} in {path}, {idx+1}/{len(files)}')

                _r = parse_map_fname(f)
                if _r:
                    src, dst, ver, idx = _r
                    _handle_map(src, dst, ver, idx, None)
                    continue

                _r = parse_large_fname(f)
                if _r:
                    src, dst, ver, idx, hash = _r
                    _handle_map(src, dst, ver, idx, hash)
                    continue
                    
                _r = parse_obj_fname(f)
                if _r:
                    name, idx, ext = _r
                    _handle_obj(name, idx, ext)
                    continue
                _logger.warning(f'Unrecognized file: {f}')

    # transform maps and objs   
    _ls_maps = {}
    for k, v in _maps.items():
        _to_drop = []
        for ver, vv in v.items():
            # convert shards to list
            _ls = [None] * 2**vv['sharding_bits']
            for kkk, vvv in vv['shards'].items():
                _ls[kkk] = vvv
            # see if we can find the None in _ls
            _nones = [i for i, x in enumerate(_ls) if x is None]
            if _nones:
                _logger.warning(f'Cannot find shards {", ".join(map(str, _nones))} in map {k} ver {ver}, skipping')
                _logger.warning(f"Got: {vv['shards']}")
                _to_drop.append(ver)
            else:
                vv['shards'] = _ls
        for ver in _to_drop:
            del v[ver]

        # move latest maps to the front of the list
        _ls_maps[k] = [v for k, v in sorted(
            v.items(), 
            key=cmp_to_key(lambda x, y: compare_woc_version(x[0], y[0])),
            reverse=True
        )]

    _ls_objs = {}
    for k, v in _objs.items():
        # convert shards to list
        _ls = [None] * 2**v['sharding_bits']
        for kk, vv in v['shards'].items():
            _ls[kk] = vv
        # see if we can find the None in _ls
        _nones = [i for i, x in enumerate(_ls) if x is None]
        if _nones:
            _logger.warning(f'Cannot find shards {", ".join(map(str, _nones))} in obj {k}, skipping')
            _logger.warning(f"Got: {v['shards']}")
        else:
            v['shards'] = _ls
            _ls_objs[k] = v

                
    # load the preset profile
    with open(preset_path, 'r') as f:
        res = json.load(f)

    res["maps"] = _ls_maps
    res["objects"] = _ls_objs
    return res

parser = argparse.ArgumentParser(description='Detect woc profile')
parser.add_argument('paths', metavar='PATH', type=str, nargs='+', help='path to woc directory')
parser.add_argument('--version', type=str, default=None, help='woc mapping version')
parser.add_argument('--preset', type=str, default=DEFAULT_PROFILE, help='path to preset profile')
parser.add_argument('--output', type=str, default=None, help='path to output profile')


if __name__ == '__main__':
    import doctest
    doctest.testmod()

    args = parser.parse_args()
    
    res = detect_profile(args.paths, args.version, args.preset)
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(res, f, indent=2)
    else:
        print(json.dumps(res, indent=2))