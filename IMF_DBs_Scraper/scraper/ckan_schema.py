from dataclasses import dataclass, field
from typing import List, Dict, Optional
from dateutil.parser import parse
from datetime import datetime
import os
import json


def default_tags():
    return [Tag(name="unclassified")]


def default_additional_data_sources():
    return [AdditionalDataSource(name="", url="")]


@dataclass
class AdditionalDataSource:
    name: str = ""
    url: str = ""

    def to_dict(self):
        return {"name": self.name, "url": self.url}


@dataclass
class Tag:
    name: str = "unclassified"

    def to_dict(self):
        return {"name": self.name}


@dataclass
class CKANSchema:
    table: str
    description: str
    url: str = ""
    source: str = ""
    indicator: str = ""
    additional_data_sources: List[AdditionalDataSource] = field(default_factory=default_additional_data_sources)
    tags: List[Tag] = field(default_factory=default_tags)
    limitations: str = ""
    concept: str = ""
    periodicity: str = ""
    topic: str = ""
    created: str = ""
    last_modified: str = ""

    def __post_init__(self):
        date_formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]

        if self.created:
            for date_format in date_formats:
                try:
                    datetime.strptime(self.created, date_format)
                    break
                except ValueError:
                    pass
            else:
                raise ValueError(f"Invalid date format for 'created': {self.created}")

        if self.last_modified:
            for date_format in date_formats:
                try:
                    datetime.strptime(self.last_modified, date_format)
                    break
                except ValueError:
                    pass
            else:
                raise ValueError(f"Invalid date format for 'last_modified': {self.last_modified}")

    def to_dict(self):
        return {
            "url": self.url,
            "source": self.source,
            "indicator": self.indicator,
            "additional_data_sources": [source.to_dict() if isinstance(source, AdditionalDataSource) else source for
                                        source in self.additional_data_sources],
            "table": self.table,
            "description": self.description,
            "tags": [tag.to_dict() if isinstance(tag, Tag) else tag for tag in self.tags],
            "limitations": self.limitations,
            "concept": self.concept,
            "periodicity": self.periodicity,
            "topic": self.topic,
            "created": self.created,
            "last_modified": self.last_modified,
        }


def save_to_json(schema: CKANSchema, file_name: str, file_location: str):
    file_path = os.path.join(file_location, file_name)

    with open(file_path, "w") as f:
        json.dump(schema.to_dict(), f, indent=4)
    print('Saved metadata Successfully!')

