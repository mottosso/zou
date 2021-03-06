from flask_restful import current_app

from zou.app.models.preview_file import PreviewFile
from zou.app.models.task import Task
from zou.app.models.person import Person

from zou.app.project import asset_info, shot_info

from zou.app.resources.source.shotgun.base import (
    BaseImportShotgunResource,
    ImportRemoveShotgunBaseResource
)


class ImportShotgunVersionsResource(BaseImportShotgunResource):

    def __init__(self):
        BaseImportShotgunResource.__init__(self)

    def prepare_import(self):
        self.person_ids = Person.get_id_map()
        self.task_ids = Task.get_id_map()
        self.asset_ids = self.get_asset_map()
        self.shot_ids = self.get_shot_map()

    def get_asset_map(self):
        assets = asset_info.get_assets()
        return {asset.shotgun_id: asset.id for asset in assets}

    def get_shot_map(self):
        shots = shot_info.get_shots()
        return {shot.shotgun_id: shot.id for shot in shots}

    def filtered_entries(self):
        return (x for x in self.sg_entries if self.is_version_linked_to_task(x))

    def is_version_linked_to_task(self, version):
        return version["sg_task"] is not None

    def extract_data(self, sg_version):
        data = {
            "name": sg_version["code"],
            "shotgun_id": sg_version["id"],
            "description": sg_version["description"],
            "source": "Shotgun"
        }

        if "user" in sg_version and sg_version["user"] is not None:
            data["person_id"] = self.person_ids.get(
                sg_version["user"]["id"],
                None
            )

        if sg_version["entity"] is not None:
            data["entity_id"] = self.get_entity_id(sg_version["entity"])

        if sg_version["sg_task"] is not None:
            data["task_id"] = self.task_ids.get(
                sg_version["sg_task"]["id"],
                None
            )

        if sg_version["sg_uploaded_movie"] is not None:
            data["uploaded_movie_url"] = \
                sg_version["sg_uploaded_movie"]["url"]
            data["uploaded_movie_name"] = \
                sg_version["sg_uploaded_movie"]["name"]

        return data

    def get_entity_id(self, sg_entity):
        entity_sg_id = sg_entity["id"]
        entity_type = sg_entity["type"]
        entity_id = None
        if entity_type == "Asset":
            entity_id = self.asset_ids.get(entity_sg_id, None)
        else:
            entity_id = self.shot_ids.get(entity_sg_id, None)
        return entity_id

    def import_entry(self, data):
        preview_file = PreviewFile.get_by(shotgun_id=data["shotgun_id"])
        if preview_file is None:
            preview_file = PreviewFile.get_by(
                name=data["name"],
                task_id=data["task_id"]
            )

        if preview_file is None:
            preview_file = PreviewFile(**data)
            preview_file.save()
            current_app.logger.info("PreviewFile created: %s" % preview_file)
        else:
            preview_file.update(data)
            current_app.logger.info("PreviewFile updated: %s" % preview_file)
        return preview_file


class ImportRemoveShotgunVersionResource(ImportRemoveShotgunBaseResource):

    def __init__(self):
        ImportRemoveShotgunBaseResource.__init__(self, PreviewFile)
