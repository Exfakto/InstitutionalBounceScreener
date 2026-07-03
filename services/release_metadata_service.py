from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, asdict

from config.app_metadata import (
    APPLICATION_NAME,
    BUILD_DATE,
    BUILD_TIMESTAMP,
    RELEASE_CHANNEL,
    SCHEMA_VERSION,
    VERSION,
)
from services.resource_path_service import ResourcePathService


@dataclass(frozen=True)
class ReleaseMetadata:
    application_name: str = APPLICATION_NAME
    version: str = VERSION
    build_date: str = BUILD_DATE
    build_timestamp: str = BUILD_TIMESTAMP
    release_channel: str = RELEASE_CHANNEL
    schema_version: str = SCHEMA_VERSION
    python_version: str = sys.version.split()[0]
    platform: str = platform.platform()
    packaged: bool = ResourcePathService.is_packaged()

    def to_dict(self):
        return asdict(self)


class ReleaseMetadataService:
    def metadata(self):
        return ReleaseMetadata()

    def build_environment_summary(self):
        metadata = self.metadata()
        return {
            "python_version": metadata.python_version,
            "platform": metadata.platform,
            "packaged": metadata.packaged,
            "release_channel": metadata.release_channel,
        }
