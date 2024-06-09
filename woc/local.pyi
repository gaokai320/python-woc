from typing import Iterable, Union, Tuple, List

from .base import WocMapsBase, WocObjectsWithContent

class WocMapsLocal(WocMapsBase):
    def __init__(self, 
            profile_path: str | Iterable[str] | None = None,
            version: str | Iterable[str] | None = None
        ) -> None: 
        ...
        
    def _get_tch_bytes(
        self, map_name: str, key: Union[bytes, str]
    ) -> Tuple[bytes, str]:
        ...
        
    def _get_pos(
        self, obj_name: str, key: Union[bytes, str],
    ) -> Tuple[int, int]:
        """
        Get offset and length of a stacked binary object, currently only support blob.
        Extract this part because it's much cheaper than decode the content.
        >>> self._get_pos('blob', bytes.fromhex('7a374e58c5b9dec5f7508391246c48b73c40d200'))
        (0, 123)
        """
        ...

# The following functions are internal and should not be used by the user
# Exposing them here for testing purposes
def fnvhash(data: bytes) -> int: ...
def unber(buf: bytes) -> bytes: ...
def lzf_length(raw_data: bytes) -> Tuple[int, int]: ...
def decomp(data: bytes) -> bytes: ...
def decomp_or_raw(data: bytes) -> bytes: ...
def get_tch(path: str): ...
def get_shard(key: bytes, sharding_bits: int, use_fnv_keys: bool) -> int: ...
# def get_from_tch(key: bytes, shards: List[bytes], sharding_bits: int, use_fnv_keys: bool) -> bytes: ...
def decode_value(value: bytes, out_dtype: str): ...
def decode_tree(value: bytes) -> List[Tuple[str, str, str]]: ...
def decode_commit(commit_bin: bytes) -> Tuple[str, Tuple[str, str, str], Tuple[str, str, str], str]: ...
def decode_str(raw_data: str, encoding='utf-8'): ...
