from dataclasses import dataclass

from attendance_app.domain.errors import ValidationError


@dataclass(frozen=True)
class PersonInput:
    first_name: str
    last_name: str
    person_id: str
    optional_info: str = ""

    def validated(self):
        values = []
        for value, label in ((self.first_name, "نام"), (self.last_name, "نام خانوادگی"), (self.person_id, "شناسه")):
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(label + " را به صورت متن وارد کنید.")
            values.append(value.strip())
        if not isinstance(self.optional_info, str):
            raise ValidationError("اطلاعات تکمیلی باید متن باشد.")
        return PersonInput(*values, self.optional_info.strip())


@dataclass(frozen=True)
class Person:
    id: int
    person_id: str
    first_name: str
    last_name: str
    optional_info: str
    created_at: str
    is_active: bool

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


def normalize_search(text: str) -> str:
    # Only search is normalized; original names and identifiers remain untouched.
    return " ".join(text.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})).casefold().split())
