from dataclasses import dataclass
from typing import Any, Tuple
import os

from .project import ProjectConfiguration, ProjectConfigurationBase, ProjectConfigurationDefaults
from .collection import CollectionConfiguration, CollectionConfigurationBase

@dataclass
class ConfigurationBase(ProjectConfigurationBase, CollectionConfigurationBase):
    pass

@dataclass
class ConfigurationDefaults(ProjectConfigurationDefaults):
    args: Any = None

@dataclass
class Configuration(ProjectConfiguration, CollectionConfiguration, ConfigurationBase, ConfigurationDefaults):
    def __post_init__(self):
        try:
            Configuration.validate(self)
        except Exception as e:
            raise e

    @classmethod
    def validate(cls, self):
        pass

    @classmethod
    def create_subclasses(cls, args: Any) -> Tuple[ProjectConfiguration, CollectionConfiguration]:
        root_path = os.getcwd()
        if hasattr(args, 'project_dir'):
            root_path = args.project_dir

        project = ProjectConfiguration.from_root_path(root_path)

        collection_name = (project.collection_name or 'default')
        source_name = (project.source_name or 'default')
        collection = CollectionConfiguration.from_args(
            collection_name=collection_name, 
            source_name=source_name,
            args=args
        )

        return (project, collection)

    @classmethod
    def from_subclasses(cls, project: ProjectConfiguration, collection: CollectionConfiguration, args) -> 'Configuration':
        return cls(
            project_name=project.project_name,
            version=project.version,
            root_path=project.root_path,
            monitor_paths=project.monitor_paths,
            collection_name=project.collection_name,
            source_name=project.source_name,
            reporter=project.reporter,
            config=collection.config,
            args=args)


    @classmethod
    def from_args(cls, args: Any) -> 'Configuration':
        project, collection = cls.create_subclasses(args)
        configuration = cls.from_subclasses(
            project=project,
            collection=collection,
            args=args
        )

        return configuration

