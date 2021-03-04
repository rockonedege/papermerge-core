from papermerge.core.importers import BaseImporter


class RestApiImporter(BaseImporter):

    def get_parent_id(self):
        """
        Imported documents via REST API always land in user's Inbox
        """
        parent_id = self.parent_id

        if parent_id is None:
            _, _, inbox = self.get_user_properties(self.user)
            parent_id = inbox.id

        return parent_id
