import base64
import binascii
from uuid import uuid4

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):
    """Преобразует Base64-строку в файл изображения."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            try:
                header, encoded_image = data.split(';base64,', 1)
                extension = header.split('/')[-1].lower()
                decoded_image = base64.b64decode(
                    encoded_image,
                    validate=True,
                )
            except (ValueError, TypeError, binascii.Error) as error:
                raise serializers.ValidationError(
                    'Некорректное изображение в формате Base64.'
                ) from error

            if extension == 'jpeg':
                extension = 'jpg'

            data = ContentFile(
                decoded_image,
                name=f'{uuid4().hex}.{extension}',
            )

        return super().to_internal_value(data)