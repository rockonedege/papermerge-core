import logging
from os.path import getsize, basename
from tempfile import _TemporaryFileWrapper

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import TemporaryUploadedFile

from papermerge.core.storage import default_storage
from papermerge.core.tasks import ocr_page
from papermerge.core.pipelines import Pipelines
from papermerge.core.models import Document


logger = logging.getLogger(__name__)


class BaseImporter:
    """
    Base class for import interfaces:

        * imap - import documents from email attachments
        * local - import documents from local directory
        * web - import document by user upload via WEB
        * rest_api - import document via REST API
    """

    def __init__(
        self,
        payload,
        filename,
        user,
        parent_id,
        lang,
        skip_ocr,
    ):
        self.payload = payload
        self.filename = filename
        self.user = user
        self.parent_id = parent_id
        self.lang = lang
        self.skip_ocr = skip_ocr

    def __call__(self):

        payload = self.payload

        for pipeline in Pipelines():
            new_payload = pipeline(payload)
            payload = new_payload

        # create document with payload given
        # by last pipeline
        self.create_document(payload=payload)

    def get_parent_id(self):
        return self.parent_id

    def get_path(self, payload):

        payload_path = None

        if isinstance(payload, TemporaryUploadedFile):
            payload_path = payload.temporary_file_path()
        elif isinstance(payload, _TemporaryFileWrapper):
            payload_path = payload.name
        else:
            raise TypeError

        return payload_path

    def get_filename(self, payload):
        filename = self.filename
        if not filename:
            filename = basename(self.get_path(payload))

        return filename

    def create_document(self, payload):

        filename = self.get_filename(payload)
        page_count = self.page_count()
        size = getsize(self.get_path(payload))

        try:
            doc = Document.objects.create_document(
                user=self.user,
                title=filename,
                size=size,
                lang=self.lang,
                file_name=filename,
                parent_id=self.get_parent_id(),
                page_count=page_count,
            )
            self.doc = doc
        except ValidationError as error:
            logger.error(f"{self.processor} importer: validation failed")
            raise error

        self.move_tempfile(doc)
        self.payload.close()
        if not self.skip_ocr:

            namespace = default_storage.upload(
                doc_path_url=doc.path().url()
            )

            if self.apply_async:
                for page_num in range(1, page_count + 1):
                    ocr_page.apply_async(kwargs={
                        'user_id': self.user.id,
                        'document_id': doc.id,
                        'file_name': filename,
                        'page_num': page_num,
                        'lang': self.lang,
                        'namespace': namespace
                    })
            else:
                self.ocr_document(
                    document=doc,
                    page_count=page_count,
                    lang=self.lang,
                )

        logger.debug(f"{self.processor} importer: import complete.")
        return doc
