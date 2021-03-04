from papermerge.core.pipelines import Pipelines


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

    def create_document(self, payload):
        pass
