from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote, unquote, urlparse

from swallow.surface_tools.paths import artifacts_dir
from swallow.surface_tools.workspace import resolve_path


SUPPORTED_RAW_MATERIAL_SCHEMES: tuple[str, ...] = ("file", "artifact")
FUTURE_RAW_MATERIAL_SCHEMES: tuple[str, ...] = ("s3", "minio", "oss")
WORKSPACE_FILE_AUTHORITY = "workspace"
RAW_MATERIAL_HASH_ALGORITHM = "sha256"
LEGACY_ARTIFACT_REF_PREFIX: tuple[str, ...] = (".swl", "tasks")


class RawMaterialError(ValueError):
    """Base error for invalid or unsupported raw material references."""


class InvalidRawMaterialRef(RawMaterialError):
    """Raised when a raw material reference is malformed or unsafe."""


class UnsupportedRawMaterialScheme(RawMaterialError):
    """Raised when a store does not support a raw material URI scheme."""


@dataclass(frozen=True, slots=True)
class RawMaterialRef:
    scheme: str
    key: str
    fragment: str = ""

    def __post_init__(self) -> None:
        normalized_scheme = self.scheme.strip().lower()
        normalized_key = self.key.strip()
        normalized_fragment = self.fragment.strip()
        if not normalized_scheme:
            raise InvalidRawMaterialRef("raw material source_ref must include a URI scheme")
        if not normalized_key:
            raise InvalidRawMaterialRef("raw material source_ref must include a non-empty key")
        object.__setattr__(self, "scheme", normalized_scheme)
        object.__setattr__(self, "key", normalized_key)
        object.__setattr__(self, "fragment", normalized_fragment)


class RawMaterialStore(Protocol):
    def resolve(self, source_ref: str) -> bytes:
        """Return raw material bytes for a stable source_ref."""

    def exists(self, source_ref: str) -> bool:
        """Return whether the raw material referenced by source_ref exists."""

    def content_hash(self, source_ref: str) -> str:
        """Return a backend-appropriate content hash for source_ref."""


def parse_source_ref(source_ref: str) -> RawMaterialRef:
    normalized = source_ref.strip()
    if not normalized:
        raise InvalidRawMaterialRef("source_ref must be a non-empty string")

    parsed = urlparse(normalized)
    if not parsed.scheme:
        raise InvalidRawMaterialRef("source_ref must include a URI scheme")

    return RawMaterialRef(
        scheme=parsed.scheme,
        key=_combined_uri_key(parsed.netloc, parsed.path),
        fragment=unquote(parsed.fragment or ""),
    )


def source_ref_for_file(path: Path, *, workspace_root: Path | None = None) -> str:
    resolved_path = resolve_path(path)
    if workspace_root is None:
        return resolved_path.as_uri()

    resolved_workspace = resolve_path(workspace_root)
    try:
        relative_path = resolved_path.relative_to(resolved_workspace)
    except ValueError:
        return resolved_path.as_uri()

    key = _quote_posix_path(PurePosixPath(WORKSPACE_FILE_AUTHORITY) / relative_path.as_posix())
    return f"file://{key}"


def source_ref_for_artifact(task_id: str, artifact_name: str) -> str:
    normalized_task_id = _normalize_uri_segment(task_id, field_name="task_id")
    artifact_path = _normalize_relative_posix_path(artifact_name, field_name="artifact_name")
    return f"artifact://{quote(normalized_task_id, safe='._-')}/{_quote_posix_path(artifact_path)}"


def artifact_source_ref_from_legacy_ref(artifact_ref: str) -> str:
    normalized = artifact_ref.strip()
    if not normalized:
        raise InvalidRawMaterialRef("artifact_ref must be a non-empty string")
    if parse_source_ref_scheme(normalized) == "artifact":
        _parse_artifact_key(parse_source_ref(normalized).key)
        return normalized

    ref_without_fragment, fragment = _split_fragment(normalized)
    parts = PurePosixPath(ref_without_fragment).parts
    if len(parts) < 5 or parts[:2] != LEGACY_ARTIFACT_REF_PREFIX or parts[3] != "artifacts":
        raise InvalidRawMaterialRef("legacy artifact_ref must match .swl/tasks/<task_id>/artifacts/<artifact_path>")

    task_id = parts[2]
    artifact_path = PurePosixPath(*parts[4:]).as_posix()
    source_ref = source_ref_for_artifact(task_id, artifact_path)
    if fragment:
        return f"{source_ref}#{quote(fragment, safe='._-/')}"
    return source_ref


def parse_source_ref_scheme(source_ref: str) -> str:
    return urlparse(source_ref.strip()).scheme.strip().lower()


class FilesystemRawMaterialStore:
    def __init__(self, base_dir: Path, *, workspace_root: Path | None = None) -> None:
        self.base_dir = resolve_path(base_dir)
        self.workspace_root = resolve_path(workspace_root or base_dir)

    def resolve(self, source_ref: str) -> bytes:
        return self._path_for(source_ref).read_bytes()

    def exists(self, source_ref: str) -> bool:
        return self._path_for(source_ref).is_file()

    def content_hash(self, source_ref: str) -> str:
        digest = hashlib.sha256(self._path_for(source_ref).read_bytes()).hexdigest()
        return f"{RAW_MATERIAL_HASH_ALGORITHM}:{digest}"

    def _path_for(self, source_ref: str) -> Path:
        ref = parse_source_ref(source_ref)
        if ref.scheme == "file":
            return self._file_path_for(ref)
        if ref.scheme == "artifact":
            return self._artifact_path_for(ref)
        raise UnsupportedRawMaterialScheme(f"unsupported raw material scheme for filesystem store: {ref.scheme}")

    def _file_path_for(self, ref: RawMaterialRef) -> Path:
        key_path = PurePosixPath(ref.key)
        if key_path.is_absolute():
            return resolve_path(Path(ref.key))

        relative_key = ref.key
        if ref.key == WORKSPACE_FILE_AUTHORITY:
            relative_key = "."
        elif ref.key.startswith(f"{WORKSPACE_FILE_AUTHORITY}/"):
            relative_key = ref.key.removeprefix(f"{WORKSPACE_FILE_AUTHORITY}/")

        return _resolve_under_root(
            self.workspace_root,
            relative_key,
            field_name="file source_ref",
        )

    def _artifact_path_for(self, ref: RawMaterialRef) -> Path:
        task_id, artifact_path = _parse_artifact_key(ref.key)
        artifact_root = resolve_path(artifacts_dir(self.base_dir, task_id))
        return _resolve_under_root(
            artifact_root,
            artifact_path,
            field_name="artifact source_ref",
        )


def _combined_uri_key(netloc: str, path: str) -> str:
    decoded_netloc = unquote(netloc or "")
    decoded_path = unquote(path or "")
    if decoded_netloc:
        suffix = decoded_path.lstrip("/")
        return f"{decoded_netloc}/{suffix}" if suffix else decoded_netloc
    return decoded_path


def _split_fragment(ref: str) -> tuple[str, str]:
    if "#" not in ref:
        return ref, ""
    raw_ref, fragment = ref.split("#", 1)
    return raw_ref, fragment


def _normalize_uri_segment(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise InvalidRawMaterialRef(f"{field_name} must be non-empty")
    if "/" in normalized or "\\" in normalized or normalized in {".", ".."}:
        raise InvalidRawMaterialRef(f"{field_name} must be a single URI path segment")
    return normalized


def _normalize_relative_posix_path(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise InvalidRawMaterialRef(f"{field_name} must be non-empty")
    posix_path = PurePosixPath(normalized)
    if posix_path.is_absolute():
        raise InvalidRawMaterialRef(f"{field_name} must be relative")
    if any(part in {"", ".", ".."} for part in posix_path.parts):
        raise InvalidRawMaterialRef(f"{field_name} must not contain traversal segments")
    return posix_path.as_posix()


def _resolve_under_root(root: Path, relative_path: str, *, field_name: str) -> Path:
    normalized_relative = _normalize_relative_posix_path(relative_path, field_name=field_name)
    resolved_root = resolve_path(root)
    resolved_path = resolve_path(Path(normalized_relative), base=resolved_root)
    if not resolved_path.is_relative_to(resolved_root):
        raise InvalidRawMaterialRef(f"{field_name} escapes its storage root")
    return resolved_path


def _parse_artifact_key(key: str) -> tuple[str, str]:
    key_path = PurePosixPath(key)
    if key_path.is_absolute():
        raise InvalidRawMaterialRef("artifact source_ref key must be relative")
    if len(key_path.parts) < 2:
        raise InvalidRawMaterialRef("artifact source_ref must be artifact://<task_id>/<artifact_path>")
    task_id = _normalize_uri_segment(key_path.parts[0], field_name="task_id")
    artifact_path = _normalize_relative_posix_path(
        PurePosixPath(*key_path.parts[1:]).as_posix(),
        field_name="artifact_path",
    )
    return task_id, artifact_path


def _quote_posix_path(value: PurePosixPath | str) -> str:
    return quote(PurePosixPath(value).as_posix(), safe="/._-")
