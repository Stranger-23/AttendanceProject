"""People use cases, independent of Qt and SQL."""
from attendance_app.domain.errors import PersonNotFoundError


class PeopleService:
    def __init__(self, repository):
        self.repository = repository

    def create(self, data):
        return self.repository.create(data.validated())

    def update(self, internal_id, data):
        return self.repository.update(internal_id, data.validated())

    def get(self, internal_id):
        person = self.repository.get(internal_id)
        if person is None:
            raise PersonNotFoundError()
        return person

    def search(self, query='', *, active=True):
        return self.repository.search(query, active=active)

    def archive(self, internal_id):
        self.repository.archive(internal_id)
