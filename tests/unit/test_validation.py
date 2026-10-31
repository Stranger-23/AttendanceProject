import unittest
from attendance_app.domain.errors import ValidationError
from attendance_app.domain.people import PersonInput


class ValidationTests(unittest.TestCase):
    def test_required_fields(self):
        for data in (PersonInput('', 'احمدی', '01'), PersonInput('علی', '  ', '01'), PersonInput('علی', 'احمدی', ''), PersonInput('علی', 'احمدی', 12)):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                data.validated()

    def test_ids_are_text_and_digits_are_not_transformed(self):
        for identifier in ('0012', '۰۰۱۲', '٠٠١٢', 'AB-01'):
            data = PersonInput(' علی ', ' احمدی ', identifier).validated()
            self.assertIsInstance(data.person_id, str)
            self.assertEqual(data.person_id, identifier)
            self.assertEqual(data.first_name, 'علی')
            self.assertEqual(data.optional_info, '')
